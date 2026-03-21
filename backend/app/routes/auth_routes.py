# app/routes/auth_routes.py
# AquaSense — Authentication routes
# Kulith's exact auth_routes.py ported from supabase-py → SQLAlchemy.
# All endpoint URLs, logic, rate limits, and response shapes preserved exactly.
#
# Changes:
#   supabase.table("users").select().eq().execute()
#     → db.execute(select(User).where(...))
#   supabase.table("users").update().eq().execute()
#     → user.field = value; await db.commit()
#   supabase.table("blacklisted_tokens").insert()
#     → db.add(BlacklistedToken(...)); await db.commit()
#   supabase.table("failed_attempts") calls
#     → app.utils.lock_user helpers (already ported)

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user, oauth2_scheme,
)
from config import settings
from database import get_db
from email_utils import generate_otp, send_email, send_login_alert_email
from models import User, BlacklistedToken
from schemas import (
    RegisterSchema, LoginSchema, VerifyOTPSchema,
    ForgotPasswordSchema, ResetPasswordSchema,
    ChangePasswordSchema, RefreshTokenSchema,
    Verify2FASchema,
)
from app.utils.lock_user import (
    is_account_locked,
    record_failed_attempt,
    reset_failed_attempts,
    MAX_FAILED_ATTEMPTS,
)

from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/auth", tags=["Auth"])
limiter = Limiter(key_func=get_remote_address)
OTP_EXPIRE_MINUTES = 10


# ─────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────

@router.post("/register")
@limiter.limit("5/minute")
async def register(
    request:          Request,
    user:             RegisterSchema,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    result   = await db.execute(select(User).where(User.email == user.email))
    existing = result.scalar_one_or_none()

    if existing:
        if not existing.is_verified:
            # Resend OTP if account exists but is unverified
            otp                      = generate_otp()
            existing.otp             = otp
            existing.otp_expires_at  = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
            existing.otp_type        = "verification"
            await db.commit()
            background_tasks.add_task(send_email, user.email, otp, "verification")
            return {"message": "OTP resent to email. Please verify your account."}
        raise HTTPException(status_code=400, detail="Email already registered and verified")

    otp        = generate_otp()
    new_user   = User(
        email           = user.email,
        password_hash   = hash_password(user.password),
        name            = user.name,
        phone_encrypted = _encrypt(user.phone) if user.phone else None,
        is_verified     = False,
        auth_provider   = "local",
        otp             = otp,
        otp_expires_at  = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
        otp_type        = "verification",
        two_fa_enabled  = False,
        login_alerts    = True,
        auto_lock_minutes = 30,
    )
    db.add(new_user)
    await db.commit()

    background_tasks.add_task(send_email, user.email, otp, "verification")
    return {"message": "User registered. OTP sent to email. Valid for 10 minutes."}


# ─────────────────────────────────────────────
# VERIFY OTP
# ─────────────────────────────────────────────

@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(
    request: Request,
    data:    VerifyOTPSchema,
    db:      AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    if user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if user.otp_expires_at and datetime.now(timezone.utc) > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")

    user.is_verified    = True
    user.otp            = None
    user.otp_expires_at = None
    user.otp_type       = None
    await db.commit()

    return {"message": "Email verified successfully"}


# ─────────────────────────────────────────────
# RESEND OTP
# ─────────────────────────────────────────────

@router.post("/resend-otp")
@limiter.limit("3/minute")
async def resend_otp(
    request:          Request,
    email:            str,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")

    otp                 = generate_otp()
    user.otp            = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    user.otp_type       = "verification"
    await db.commit()

    background_tasks.add_task(send_email, email, otp, "verification")
    return {"message": "New OTP sent to email. Valid for 10 minutes."}


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

@router.post("/login")
@limiter.limit("20/minute")
async def login(
    request:          Request,
    user:             LoginSchema,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    db_user = None

    if user.email:
        result  = await db.execute(select(User).where(User.email == user.email))
        db_user = result.scalar_one_or_none()
    elif user.phone:
        # Phone is encrypted — must compare decrypted values
        all_result = await db.execute(select(User))
        for u in all_result.scalars().all():
            if u.phone_encrypted:
                try:
                    if _decrypt(u.phone_encrypted) == user.phone:
                        db_user = u
                        break
                except Exception:
                    continue

    if not db_user:
        raise HTTPException(status_code=404,
                            detail="No account found with this email or phone number")
    if not db_user.is_verified:
        raise HTTPException(status_code=403,
                            detail="Email not verified. Please verify your email before logging in")
    if db_user.password_hash is None:
        raise HTTPException(status_code=400,
                            detail="This account has no password set. Please login using Google or use forgot password to set one")

    identifier = db_user.email

    locked, minutes_remaining = await is_account_locked(identifier, db)
    if locked:
        raise HTTPException(
            status_code=423,
            detail=f"Account is temporarily locked due to too many failed attempts. Try again in {minutes_remaining} minutes"
        )

    if not verify_password(user.password, db_user.password_hash):
        await record_failed_attempt(identifier, db)

        # Count remaining attempts
        from models import FailedAttempt
        fa_result    = await db.execute(
            select(FailedAttempt).where(FailedAttempt.identifier == identifier)
        )
        fa_record    = fa_result.scalar_one_or_none()
        attempts_used = fa_record.attempts if fa_record else 1
        attempts_left = max(0, MAX_FAILED_ATTEMPTS - attempts_used)

        raise HTTPException(
            status_code=400,
            detail=f"Incorrect password. {attempts_left} attempts remaining before account is locked"
        )

    await reset_failed_attempts(identifier, db)

    access_token  = create_access_token({"sub": db_user.email})
    refresh_token = create_refresh_token({"sub": db_user.email})

    # Store refresh token on user row (Kulith's pattern)
    db_user.otp = None  # clear any stale OTPs on login

    if db_user.login_alerts:
        login_time  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        device_info = request.headers.get("User-Agent", "Unknown device")
        background_tasks.add_task(
            send_login_alert_email,
            db_user.email,
            db_user.name or "User",
            device_info,
            login_time,
        )

    if db_user.two_fa_enabled:
        otp                 = generate_otp()
        db_user.otp         = otp
        db_user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
        db_user.otp_type    = "2fa"
        await db.commit()
        background_tasks.add_task(send_email, db_user.email, otp, "2fa")
        return {
            "access_token":        access_token,
            "refresh_token":       refresh_token,
            "token_type":          "bearer",
            "two_factor_required": True,
            "message":             "2FA OTP sent to your email. Please verify to complete login.",
        }

    await db.commit()
    return {
        "access_token":        access_token,
        "refresh_token":       refresh_token,
        "token_type":          "bearer",
        "two_factor_required": False,
    }


# ─────────────────────────────────────────────
# VERIFY 2FA AFTER LOGIN
# ─────────────────────────────────────────────

@router.post("/2fa/verify-login")
async def verify_2fa_login(
    data:         Verify2FASchema,
    current_user  = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    if current_user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    if current_user.otp_expires_at and datetime.now(timezone.utc) > current_user.otp_expires_at:
        raise HTTPException(status_code=400, detail="2FA code has expired. Please login again")

    current_user.otp            = None
    current_user.otp_expires_at = None
    current_user.otp_type       = None
    await db.commit()

    return {"message": "2FA verified successfully. You are now logged in."}


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────

@router.post("/logout")
async def logout(
    current_user  = Depends(get_current_user),
    token:  str   = Depends(oauth2_scheme),
    db:           AsyncSession = Depends(get_db),
):
    # Blacklist the access token so it cannot be used again
    existing = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.token == token)
    )
    if not existing.scalar_one_or_none():
        db.add(BlacklistedToken(token=token))
    await db.commit()

    return {"message": "Logged out successfully"}


# ─────────────────────────────────────────────
# REFRESH TOKEN
# ─────────────────────────────────────────────

@router.post("/refresh-token")
async def refresh_token_endpoint(
    data: RefreshTokenSchema,
    db:   AsyncSession = Depends(get_db),
):
    # Check if already blacklisted
    bl = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.token == data.refresh_token)
    )
    if bl.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="Refresh token is invalid or has been revoked")

    try:
        payload    = jwt.decode(data.refresh_token, settings.JWT_SECRET,
                                algorithms=[settings.JWT_ALGORITHM])
        email      = payload.get("sub")
        token_type = payload.get("type")

        if not email or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        result  = await db.execute(select(User).where(User.email == email, User.is_verified == True))
        db_user = result.scalar_one_or_none()
        if not db_user:
            raise HTTPException(status_code=401, detail="Refresh token is invalid or has been revoked")

        # Blacklist the old refresh token (rotation)
        db.add(BlacklistedToken(token=data.refresh_token))
        await db.commit()

        new_access  = create_access_token({"sub": email})
        new_refresh = create_refresh_token({"sub": email})

        return {
            "access_token":  new_access,
            "refresh_token": new_refresh,
            "token_type":    "bearer",
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


# ─────────────────────────────────────────────
# FORGOT PASSWORD
# ─────────────────────────────────────────────

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request:          Request,
    data:             ForgotPasswordSchema,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email address")
    if not user.is_verified:
        raise HTTPException(status_code=403,
                            detail="Email not verified. Please verify your account first")

    otp                 = generate_otp()
    user.otp            = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    user.otp_type       = "reset"
    await db.commit()

    background_tasks.add_task(send_email, data.email, otp, "reset")
    return {"message": "Password reset OTP sent to your email. Valid for 10 minutes."}


# ─────────────────────────────────────────────
# RESET PASSWORD
# ─────────────────────────────────────────────

@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    data:    ResetPasswordSchema,
    db:      AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if user.otp_expires_at and datetime.now(timezone.utc) > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")
    if user.password_hash and verify_password(data.new_password, user.password_hash):
        raise HTTPException(status_code=400,
                            detail="New password cannot be the same as your old password")

    user.password_hash  = hash_password(data.new_password)
    user.otp            = None
    user.otp_expires_at = None
    user.otp_type       = None
    await db.commit()

    return {"message": "Password reset successfully. You can now login with your new password."}


# ─────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────

@router.post("/change-password")
async def change_password(
    data:         ChangePasswordSchema,
    current_user  = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    if current_user.password_hash is None:
        raise HTTPException(status_code=400,
                            detail="This account has no password set. Please use forgot password to set one first")
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400,
                            detail="New password must be different from current password")

    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


# ── Private encryption helpers used within this file ─────────

def _encrypt(value: str) -> str:
    from app.utils.encryption import encrypt
    return encrypt(value)

def _decrypt(value: str) -> str:
    from app.utils.encryption import decrypt
    return decrypt(value)
