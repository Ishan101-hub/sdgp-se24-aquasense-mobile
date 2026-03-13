from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from datetime import datetime, timedelta, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import users_collection, blacklisted_tokens_collection, failed_attempts_collection
from app.schemas import (
    RegisterSchema, LoginSchema, VerifyOTPSchema,
    ForgotPasswordSchema, ResetPasswordSchema,
    ChangePasswordSchema, RefreshTokenSchema,
    Verify2FASchema
)
from app.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user, oauth2_scheme
)
from app.email_utils import generate_otp, send_email, send_login_alert_email
from app.utils.lock_user import (
    is_account_locked,
    record_failed_attempt,
    reset_failed_attempts,
    MAX_FAILED_ATTEMPTS
)
from jose import jwt, JWTError
from app.config import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/auth", tags=["Auth"])

OTP_EXPIRE_MINUTES = 10
limiter = Limiter(key_func=get_remote_address)


# ─────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────
@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, user: RegisterSchema, background_tasks: BackgroundTasks):
    existing_user = await users_collection.find_one({"email": user.email})

    if existing_user:
        if not existing_user.get("is_verified", False):
            otp = generate_otp()
            otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
            await users_collection.update_one(
                {"email": user.email},
                {"$set": {"otp": otp, "otp_expires_at": otp_expires_at}}
            )
            background_tasks.add_task(send_email, user.email, otp, "verification")
            return {"message": "OTP resent to email. Please verify your account."}
        raise HTTPException(status_code=400, detail="Email already registered and verified")

    hashed_pw = hash_password(user.password)
    otp = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    await users_collection.insert_one({
        "email": user.email,
        "password": hashed_pw,
        "name": user.name,
        # Phone stored as plain text so it can be used for login searches
        "phone": user.phone,
        "is_verified": False,
        "otp": otp,
        "otp_expires_at": otp_expires_at,
        "address": None,
        "profile_picture": None,
        "auth_provider": "local",
        # Security settings — defaults on registration
        # Biometric removed
        "two_factor_enabled": False,
        "login_alerts_enabled": True,
        "auto_lock_minutes": 30,
        "created_at": datetime.now(timezone.utc)
    })

    background_tasks.add_task(send_email, user.email, otp, "verification")
    return {"message": "User registered. OTP sent to email. Valid for 10 minutes."}


# ─────────────────────────────────────────────
# VERIFY OTP
# ─────────────────────────────────────────────
@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, data: VerifyOTPSchema):
    user = await users_collection.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Email is already verified")
    if user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_expires_at = user.get("otp_expires_at")
    if otp_expires_at:
        if isinstance(otp_expires_at, str):
            otp_expires_at = datetime.fromisoformat(otp_expires_at)
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > otp_expires_at:
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")

    await users_collection.update_one(
        {"email": data.email},
        {"$set": {"is_verified": True, "otp": None, "otp_expires_at": None}}
    )
    return {"message": "Email verified successfully"}


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
@router.post("/login")
@limiter.limit("20/minute")
async def login(request: Request, user: LoginSchema, background_tasks: BackgroundTasks):

    if user.email:
        # Email stored as plain text — search directly
        db_user = await users_collection.find_one({"email": user.email})
    else:
        # Phone stored as plain text — search directly
        db_user = await users_collection.find_one({"phone": user.phone})

    if not db_user:
        raise HTTPException(status_code=404, detail="No account found with this email or phone number")
    if not db_user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your email before logging in")

    if db_user.get("password") is None:
        raise HTTPException(
            status_code=400,
            detail="This account has no password set. Please login using Google or use forgot password to set one"
        )

    # Always use email as identifier for lockout tracking
    identifier = db_user.get("email")

    locked, minutes_remaining = await is_account_locked(identifier)
    if locked:
        raise HTTPException(
            status_code=423,
            detail=f"Account is temporarily locked due to too many failed attempts. Try again in {minutes_remaining} minutes"
        )

    if not verify_password(user.password, db_user["password"]):
        await record_failed_attempt(identifier)

        record = await failed_attempts_collection.find_one({"email": identifier})
        attempts_used = record.get("attempts", 1) if record else 1
        attempts_left = max(0, MAX_FAILED_ATTEMPTS - attempts_used)

        raise HTTPException(
            status_code=400,
            detail=f"Incorrect password. {attempts_left} attempts remaining before account is locked"
        )

    await reset_failed_attempts(identifier)

    access_token = create_access_token({"sub": db_user["email"]})
    refresh_token = create_refresh_token({"sub": db_user["email"]})

    await users_collection.update_one(
        {"email": db_user["email"]},
        {"$set": {"refresh_token": refresh_token}}
    )

    # Send login alert email in background if user has it enabled
    if db_user.get("login_alerts_enabled", True):
        login_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        device_info = request.headers.get("User-Agent", "Unknown device")
        background_tasks.add_task(
            send_login_alert_email,
            db_user["email"],
            db_user.get("name", "User"),
            device_info,
            login_time
        )

    # If 2FA is enabled send OTP and tell Flutter to show OTP screen
    if db_user.get("two_factor_enabled", False):
        otp = generate_otp()
        otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

        await users_collection.update_one(
            {"email": db_user["email"]},
            {"$set": {"otp": otp, "otp_expires_at": otp_expires_at}}
        )

        background_tasks.add_task(send_email, db_user["email"], otp, "2fa")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "two_factor_required": True,
            "message": "2FA OTP sent to your email. Please verify to complete login."
        }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "two_factor_required": False
    }


# ─────────────────────────────────────────────
# VERIFY 2FA AFTER LOGIN
# ─────────────────────────────────────────────
@router.post("/2fa/verify-login")
async def verify_2fa_login(
    data: Verify2FASchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    otp_expires_at = user.get("otp_expires_at")
    if otp_expires_at:
        if isinstance(otp_expires_at, str):
            otp_expires_at = datetime.fromisoformat(otp_expires_at)
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > otp_expires_at:
            raise HTTPException(status_code=400, detail="2FA code has expired. Please login again")

    await users_collection.update_one(
        {"email": current_user},
        {"$set": {"otp": None, "otp_expires_at": None}}
    )

    return {"message": "2FA verified successfully. You are now logged in."}


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────
@router.post("/logout")
async def logout(
    current_user: str = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    await blacklisted_tokens_collection.insert_one({
        "token": token,
        "blacklisted_at": datetime.now(timezone.utc)
    })
    await users_collection.update_one(
        {"email": current_user},
        {"$set": {"refresh_token": None}}
    )
    return {"message": "Logged out successfully"}


# ─────────────────────────────────────────────
# REFRESH TOKEN
# ─────────────────────────────────────────────
@router.post("/refresh-token")
async def refresh_token(data: RefreshTokenSchema):
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")

        if email is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        db_user = await users_collection.find_one({"email": email})
        if not db_user or db_user.get("refresh_token") != data.refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token is invalid or has been revoked")

        new_access_token = create_access_token({"sub": email})
        new_refresh_token = create_refresh_token({"sub": email})

        await users_collection.update_one(
            {"email": email},
            {"$set": {"refresh_token": new_refresh_token}}
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


# ─────────────────────────────────────────────
# FORGOT PASSWORD
# ─────────────────────────────────────────────
@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordSchema, background_tasks: BackgroundTasks):
    user = await users_collection.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email address")
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your account first")

    otp = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    await users_collection.update_one(
        {"email": data.email},
        {"$set": {"otp": otp, "otp_expires_at": otp_expires_at}}
    )

    background_tasks.add_task(send_email, data.email, otp, "reset")
    return {"message": "Password reset OTP sent to your email. Valid for 10 minutes."}


# ─────────────────────────────────────────────
# RESET PASSWORD
# ─────────────────────────────────────────────
@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordSchema):
    user = await users_collection.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_expires_at = user.get("otp_expires_at")
    if otp_expires_at:
        if isinstance(otp_expires_at, str):
            otp_expires_at = datetime.fromisoformat(otp_expires_at)
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > otp_expires_at:
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")

    if user.get("password") and verify_password(data.new_password, user["password"]):
        raise HTTPException(status_code=400, detail="New password cannot be the same as your old password")

    hashed_pw = hash_password(data.new_password)
    await users_collection.update_one(
        {"email": data.email},
        {"$set": {
            "password": hashed_pw,
            "otp": None,
            "otp_expires_at": None
        }}
    )
    return {"message": "Password reset successfully. You can now login with your new password."}


# ─────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────
@router.post("/change-password")
async def change_password(
    data: ChangePasswordSchema,
    current_user: str = Depends(get_current_user)
):
    db_user = await users_collection.find_one({"email": current_user})

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.get("password") is None:
        raise HTTPException(
            status_code=400,
            detail="This account has no password set. Please use forgot password to set one first"
        )

    if not verify_password(data.current_password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    hashed_pw = hash_password(data.new_password)
    await users_collection.update_one(
        {"email": current_user},
        {"$set": {"password": hashed_pw}}
    )
    return {"message": "Password changed successfully"}


# ─────────────────────────────────────────────
# RESEND OTP
# ─────────────────────────────────────────────
@router.post("/resend-otp")
@limiter.limit("3/minute")
async def resend_otp(request: Request, email: str, background_tasks: BackgroundTasks):
    user = await users_collection.find_one({"email": email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Email is already verified")

    otp = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    await users_collection.update_one(
        {"email": email},
        {"$set": {"otp": otp, "otp_expires_at": otp_expires_at}}
    )

    background_tasks.add_task(send_email, email, otp, "verification")
    return {"message": "New OTP sent to email. Valid for 10 minutes."}