# auth_router.py
# AquaSense — Authentication router
#
# Kulith's complete authentication feature set, adapted for SQLAlchemy/Supabase.
# All endpoints match Kulith's original URL structure exactly.
#
# Endpoints:
#   POST /auth/register           — create account, send email verification OTP
#   POST /auth/verify-otp         — verify email OTP → returns tokens
#   POST /auth/resend-otp         — resend verification code (rate limited)
#   POST /auth/login              — email or phone login, 2FA support, lockout
#   POST /auth/verify-2fa         — submit 2FA code → returns full tokens
#   POST /auth/refresh            — exchange refresh token for new access token
#   POST /auth/logout             — blacklist both tokens
#   POST /auth/forgot-password    — send password reset OTP
#   POST /auth/reset-password     — reset password with OTP
#   PATCH /auth/change-password   — change password while logged in

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from config import settings
from database import get_db
from email_utils import generate_otp, send_email, send_login_alert_email
from models import User, BlacklistedToken, FailedAttempt
from schemas import (
    RegisterSchema,
    LoginSchema,
    VerifyOTPSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    ChangePasswordSchema,
    RefreshTokenSchema,
)

import asyncio

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Lockout settings (same as Kulith's MongoDB version) ──────────────────────
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES     = 30
OTP_EXPIRY_MINUTES  = 10


# ── Encryption helpers (Kulith's Fernet for phone/address) ───────────────────

def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


# ── Lockout helpers ───────────────────────────────────────────────────────────

async def _check_lockout(identifier: str, db: AsyncSession) -> None:
    """Raise 429 if identifier is currently locked out."""
    result = await db.execute(
        select(FailedAttempt).where(FailedAttempt.identifier == identifier)
    )
    record = result.scalar_one_or_none()
    if record and record.locked_until:
        if datetime.now(timezone.utc) < record.locked_until:
            remaining = int(
                (record.locked_until - datetime.now(timezone.utc)).total_seconds() / 60
            )
            raise HTTPException(
                status_code=429,
                detail=f"Account locked. Try again in {remaining} minutes."
            )


async def _record_failed(identifier: str, db: AsyncSession) -> None:
    """Increment failed attempts; lock after MAX_FAILED_ATTEMPTS."""
    result = await db.execute(
        select(FailedAttempt).where(FailedAttempt.identifier == identifier)
    )
    record = result.scalar_one_or_none()
    if not record:
        record = FailedAttempt(identifier=identifier, attempts=1)
        db.add(record)
    else:
        record.attempts += 1
        if record.attempts >= MAX_FAILED_ATTEMPTS:
            record.locked_until = (
                datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            )
    await db.commit()


async def _clear_failed(identifier: str, db: AsyncSession) -> None:
    """Clear lockout after successful login."""
    await db.execute(
        delete(FailedAttempt).where(FailedAttempt.identifier == identifier)
    )
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/register
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(
    body: RegisterSchema,
    db:   AsyncSession = Depends(get_db),
):
    """
    Create a new account.
    Sends a 6-digit OTP to the email for verification.
    The account cannot log in until the OTP is verified.
    """
    existing = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    otp        = generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    user = User(
        name            = body.name,
        email           = body.email,
        password_hash   = hash_password(body.password),
        phone_encrypted = encrypt(body.phone) if body.phone else None,
        is_verified     = False,
        otp             = otp,
        otp_expires_at  = otp_expiry,
        otp_type        = "verification",
    )
    db.add(user)
    await db.commit()

    await send_email(body.email, otp, "verification")

    return {
        "message": "Account created. Please check your email for the verification code."
    }


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/verify-otp
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/verify-otp")
async def verify_otp(
    body: VerifyOTPSchema,
    db:   AsyncSession = Depends(get_db),
):
    """
    Submit the 6-digit OTP from the verification email.
    Marks the account as verified and returns access + refresh tokens.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    if user.otp != body.otp or user.otp_type != "verification":
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if not user.otp_expires_at or datetime.now(timezone.utc) > user.otp_expires_at:
        raise HTTPException(
            status_code=400,
            detail="OTP has expired. Request a new one."
        )

    user.is_verified    = True
    user.otp            = None
    user.otp_expires_at = None
    user.otp_type       = None
    await db.commit()

    access_token  = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "message":       "Email verified successfully",
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user": {
            "id":    user.id,
            "name":  user.name,
            "email": user.email,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/resend-otp
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/resend-otp")
async def resend_otp(
    body: ForgotPasswordSchema,
    db:   AsyncSession = Depends(get_db),
):
    """Resend the email verification OTP. Won't resend if OTP still has >8 minutes left."""
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    if not user:
        return {"message": "If this email is registered, a code has been sent."}
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Rate limit: don't resend if current OTP still valid for more than 8 minutes
    if user.otp_expires_at:
        remaining = (user.otp_expires_at - datetime.now(timezone.utc)).total_seconds()
        if remaining > 8 * 60:
            raise HTTPException(
                status_code=429,
                detail="A code was recently sent. Please wait before requesting another."
            )

    otp                 = generate_otp()
    user.otp            = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    user.otp_type       = "verification"
    await db.commit()

    await send_email(body.email, otp, "verification")
    return {"message": "A new verification code has been sent to your email."}


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/login
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(
    body:    LoginSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    """
    Login with email or phone + password.
    If 2FA is enabled, returns a temp token and sends OTP instead of full tokens.
    Implements account lockout after MAX_FAILED_ATTEMPTS wrong password attempts.
    """
    identifier = body.email or body.phone
    await _check_lockout(identifier, db)

    # Find user by email or by decrypting stored phone numbers
    user = None
    if body.email:
        result = await db.execute(select(User).where(User.email == body.email))
        user   = result.scalar_one_or_none()
    elif body.phone:
        all_users = await db.execute(select(User))
        for u in all_users.scalars().all():
            if u.phone_encrypted:
                try:
                    if decrypt(u.phone_encrypted) == body.phone:
                        user = u
                        break
                except Exception:
                    continue

    # Same error for wrong email/phone or wrong password — prevents user enumeration
    if not user or not verify_password(body.password, user.password_hash):
        await _record_failed(identifier, db)
        raise HTTPException(
            status_code=401,
            detail="Incorrect credentials. Please try again."
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox."
        )

    await _clear_failed(identifier, db)

    # ── 2FA path ──────────────────────────────────────────────────────────────
    if user.two_fa_enabled:
        otp                 = generate_otp()
        user.otp            = otp
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
        user.otp_type       = "2fa"
        await db.commit()
        await send_email(user.email, otp, "2fa")

        temp_token = create_access_token({"sub": user.email, "scope": "2fa_pending"})
        return {
            "message":      "2FA code sent to your email.",
            "requires_2fa": True,
            "temp_token":   temp_token,
        }

    # ── Normal login path ─────────────────────────────────────────────────────
    access_token  = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    # Send login alert if user has this setting enabled
    if user.login_alerts:
        device_info = request.headers.get("User-Agent", "Unknown device")
        time_str    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        asyncio.create_task(
            send_login_alert_email(user.email, user.name, device_info, time_str)
        )

    return {
        "message":       "Login successful",
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "requires_2fa":  False,
        "user": {
            "id":    user.id,
            "name":  user.name,
            "email": user.email,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/verify-2fa
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/verify-2fa")
async def verify_2fa(
    body: VerifyOTPSchema,
    db:   AsyncSession = Depends(get_db),
):
    """Submit the 6-digit 2FA code. Returns full access + refresh tokens on success."""
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    if user.otp != body.otp or user.otp_type != "2fa":
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    if not user.otp_expires_at or datetime.now(timezone.utc) > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="2FA code has expired")

    user.otp            = None
    user.otp_expires_at = None
    user.otp_type       = None
    await db.commit()

    access_token  = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "message":       "2FA verified successfully",
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user": {
            "id":    user.id,
            "name":  user.name,
            "email": user.email,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/refresh
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token_endpoint(
    body: RefreshTokenSchema,
    db:   AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is blacklisted (rotation pattern).
    """
    from jose import jwt as jose_jwt, JWTError

    # Reject already-blacklisted refresh tokens
    bl = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.token == body.refresh_token)
    )
    if bl.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="Refresh token has been invalidated")

    try:
        payload    = jose_jwt.decode(
            body.refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email      = payload.get("sub")
        token_type = payload.get("type")
        if not email or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    result = await db.execute(
        select(User).where(User.email == email, User.is_verified == True)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate: blacklist old refresh token, issue new pair
    db.add(BlacklistedToken(token=body.refresh_token))
    await db.commit()

    new_access  = create_access_token({"sub": email})
    new_refresh = create_refresh_token({"sub": email})

    return {
        "access_token":  new_access,
        "refresh_token": new_refresh,
        "token_type":    "bearer",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/logout
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    body:         RefreshTokenSchema,
    request:      Request,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """
    Blacklist the current access token and the provided refresh token.
    Flutter must delete both tokens from secure storage after calling this.
    """
    auth_header  = request.headers.get("Authorization", "")
    access_token = auth_header.replace("Bearer ", "").strip()

    for token in [access_token, body.refresh_token]:
        if not token:
            continue
        existing = await db.execute(
            select(BlacklistedToken).where(BlacklistedToken.token == token)
        )
        if not existing.scalar_one_or_none():
            db.add(BlacklistedToken(token=token))

    await db.commit()
    return {"message": "Logged out successfully"}


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/forgot-password
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordSchema,
    db:   AsyncSession = Depends(get_db),
):
    """
    Send a password reset OTP to the email.
    Always returns success — does not reveal if email exists.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    if user:
        otp                 = generate_otp()
        user.otp            = otp
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
        user.otp_type       = "reset"
        await db.commit()
        await send_email(body.email, otp, "reset")

    return {"message": "If this email is registered, a reset code has been sent."}


# ─────────────────────────────────────────────────────────────────────────────
#  POST /auth/reset-password
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordSchema,
    db:   AsyncSession = Depends(get_db),
):
    """Reset password using the OTP from the forgot-password email."""
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    if user.otp != body.otp or user.otp_type != "reset":
        raise HTTPException(status_code=400, detail="Invalid or incorrect OTP")
    if not user.otp_expires_at or datetime.now(timezone.utc) > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Request a new one.")
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="New password must be different from your current password"
        )

    user.password_hash  = hash_password(body.new_password)
    user.otp            = None
    user.otp_expires_at = None
    user.otp_type       = None
    await db.commit()

    return {"message": "Password reset successful. You can now log in."}


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /auth/change-password
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/change-password")
async def change_password(
    body:         ChangePasswordSchema,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """
    Change password while logged in. Requires the current password.
    Does not blacklist tokens — user stays logged in on current device.
    """
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )

    current_user.password_hash = hash_password(body.new_password)
    await db.commit()

    return {"message": "Password changed successfully."}