from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from datetime import datetime, timedelta, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import supabase
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
    # Check if email already exists in Supabase
    existing = supabase.table("users").select("*").eq("email", user.email).execute()

    if existing.data:
        existing_user = existing.data[0]
        if not existing_user.get("is_verified", False):
            otp = generate_otp()
            otp_expires_at = (
                datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
            ).isoformat()
            supabase.table("users").update({
                "otp": otp,
                "otp_expires_at": otp_expires_at
            }).eq("email", user.email).execute()
            background_tasks.add_task(send_email, user.email, otp, "verification")
            return {"message": "OTP resent to email. Please verify your account."}
        raise HTTPException(status_code=400, detail="Email already registered and verified")

    hashed_pw = hash_password(user.password)
    otp = generate_otp()
    otp_expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    ).isoformat()

    supabase.table("users").insert({
        "email": user.email,
        "password": hashed_pw,
        "name": user.name,
        "phone": user.phone,
        "is_verified": False,
        "otp": otp,
        "otp_expires_at": otp_expires_at,
        "auth_provider": "local",
        "two_factor_enabled": False,
        "login_alerts_enabled": True,
        "auto_lock_minutes": 30,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    background_tasks.add_task(send_email, user.email, otp, "verification")
    return {"message": "User registered. OTP sent to email. Valid for 10 minutes."}


# ─────────────────────────────────────────────
# VERIFY OTP
# ─────────────────────────────────────────────
@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, data: VerifyOTPSchema):
    result = supabase.table("users").select("*").eq("email", data.email).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Email is already verified")
    if user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_expires_at = user.get("otp_expires_at")
    if otp_expires_at:
        otp_expires_at_dt = datetime.fromisoformat(otp_expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > otp_expires_at_dt:
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")

    supabase.table("users").update({
        "is_verified": True,
        "otp": None,
        "otp_expires_at": None
    }).eq("email", data.email).execute()

    return {"message": "Email verified successfully"}


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
@router.post("/login")
@limiter.limit("20/minute")
async def login(request: Request, user: LoginSchema, background_tasks: BackgroundTasks):

    if user.email:
        result = supabase.table("users").select("*").eq("email", user.email).execute()
    else:
        result = supabase.table("users").select("*").eq("phone", user.phone).execute()

    db_user = result.data[0] if result.data else None

    if not db_user:
        raise HTTPException(status_code=404, detail="No account found with this email or phone number")
    if not db_user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your email before logging in")
    if db_user.get("password") is None:
        raise HTTPException(
            status_code=400,
            detail="This account has no password set. Please login using Google or use forgot password to set one"
        )

    identifier = db_user.get("email")

    locked, minutes_remaining = await is_account_locked(identifier)
    if locked:
        raise HTTPException(
            status_code=423,
            detail=f"Account is temporarily locked due to too many failed attempts. Try again in {minutes_remaining} minutes"
        )

    if not verify_password(user.password, db_user["password"]):
        await record_failed_attempt(identifier)

        attempts_result = supabase.table("failed_attempts").select("*").eq("email", identifier).execute()
        attempts_used = attempts_result.data[0].get("attempts", 1) if attempts_result.data else 1
        attempts_left = max(0, MAX_FAILED_ATTEMPTS - attempts_used)

        raise HTTPException(
            status_code=400,
            detail=f"Incorrect password. {attempts_left} attempts remaining before account is locked"
        )

    await reset_failed_attempts(identifier)

    access_token = create_access_token({"sub": db_user["email"]})
    refresh_token = create_refresh_token({"sub": db_user["email"]})

    supabase.table("users").update({
        "refresh_token": refresh_token
    }).eq("email", db_user["email"]).execute()

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

    if db_user.get("two_factor_enabled", False):
        otp = generate_otp()
        otp_expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
        ).isoformat()
        supabase.table("users").update({
            "otp": otp,
            "otp_expires_at": otp_expires_at
        }).eq("email", db_user["email"]).execute()
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
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    otp_expires_at = user.get("otp_expires_at")
    if otp_expires_at:
        otp_expires_at_dt = datetime.fromisoformat(otp_expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > otp_expires_at_dt:
            raise HTTPException(status_code=400, detail="2FA code has expired. Please login again")

    supabase.table("users").update({
        "otp": None,
        "otp_expires_at": None
    }).eq("email", current_user).execute()

    return {"message": "2FA verified successfully. You are now logged in."}


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────
@router.post("/logout")
async def logout(
    current_user: str = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    # Save token to blacklisted_tokens table so it cannot be used again
    supabase.table("blacklisted_tokens").insert({
        "token": token,
        "blacklisted_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    supabase.table("users").update({
        "refresh_token": None
    }).eq("email", current_user).execute()

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

        result = supabase.table("users").select("*").eq("email", email).execute()
        db_user = result.data[0] if result.data else None

        if not db_user or db_user.get("refresh_token") != data.refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token is invalid or has been revoked")

        new_access_token = create_access_token({"sub": email})
        new_refresh_token = create_refresh_token({"sub": email})

        supabase.table("users").update({
            "refresh_token": new_refresh_token
        }).eq("email", email).execute()

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
    result = supabase.table("users").select("*").eq("email", data.email).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email address")
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your account first")

    otp = generate_otp()
    otp_expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    ).isoformat()

    supabase.table("users").update({
        "otp": otp,
        "otp_expires_at": otp_expires_at
    }).eq("email", data.email).execute()

    background_tasks.add_task(send_email, data.email, otp, "reset")
    return {"message": "Password reset OTP sent to your email. Valid for 10 minutes."}


# ─────────────────────────────────────────────
# RESET PASSWORD
# ─────────────────────────────────────────────
@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordSchema):
    result = supabase.table("users").select("*").eq("email", data.email).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_expires_at = user.get("otp_expires_at")
    if otp_expires_at:
        otp_expires_at_dt = datetime.fromisoformat(otp_expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > otp_expires_at_dt:
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")

    if user.get("password") and verify_password(data.new_password, user["password"]):
        raise HTTPException(status_code=400, detail="New password cannot be the same as your old password")

    hashed_pw = hash_password(data.new_password)
    supabase.table("users").update({
        "password": hashed_pw,
        "otp": None,
        "otp_expires_at": None
    }).eq("email", data.email).execute()

    return {"message": "Password reset successfully. You can now login with your new password."}


# ─────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────
@router.post("/change-password")
async def change_password(
    data: ChangePasswordSchema,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    db_user = result.data[0] if result.data else None

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
    supabase.table("users").update({
        "password": hashed_pw
    }).eq("email", current_user).execute()

    return {"message": "Password changed successfully"}


# ─────────────────────────────────────────────
# RESEND OTP
# ─────────────────────────────────────────────
@router.post("/resend-otp")
@limiter.limit("3/minute")
async def resend_otp(request: Request, email: str, background_tasks: BackgroundTasks):
    result = supabase.table("users").select("*").eq("email", email).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Email is already verified")

    otp = generate_otp()
    otp_expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    ).isoformat()

    supabase.table("users").update({
        "otp": otp,
        "otp_expires_at": otp_expires_at
    }).eq("email", email).execute()

    background_tasks.add_task(send_email, email, otp, "verification")
    return {"message": "New OTP sent to email. Valid for 10 minutes."}