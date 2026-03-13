from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone, timedelta
from app.database import users_collection
from app.auth import get_current_user
from app.schemas import (
    Toggle2FASchema, Verify2FASchema,
    ToggleLoginAlertsSchema, SetAutoLockSchema
)
from app.email_utils import generate_otp, send_email

router = APIRouter(prefix="/security", tags=["Security"])

# OTP expires in 10 minutes
OTP_EXPIRE_MINUTES = 10


# ─────────────────────────────────────────────
# GET SECURITY SETTINGS
# Returns all current security settings for the logged in user
# Flutter uses this to show the current state of each toggle
# ─────────────────────────────────────────────
@router.get("/settings")
async def get_security_settings(current_user: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Biometric removed — only these three settings remain
    return {
        "two_factor_enabled": user.get("two_factor_enabled", False),
        "login_alerts_enabled": user.get("login_alerts_enabled", True),
        "auto_lock_minutes": user.get("auto_lock_minutes", 30),
    }


# ─────────────────────────────────────────────
# ENABLE TWO FACTOR AUTHENTICATION
# Step 1 — User requests to enable 2FA
# Sends an OTP to their email to confirm it is really them
# ─────────────────────────────────────────────
@router.post("/2fa/enable")
async def enable_2fa(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If 2FA is already enabled no need to enable it again
    if user.get("two_factor_enabled", False):
        raise HTTPException(status_code=400, detail="Two factor authentication is already enabled")

    # Send OTP to email to confirm it is the real user enabling 2FA
    otp = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    await users_collection.update_one(
        {"email": current_user},
        {"$set": {
            "otp": otp,
            "otp_expires_at": otp_expires_at
        }}
    )

    background_tasks.add_task(send_email, current_user, otp, "2fa")

    return {"message": "OTP sent to your email. Please verify to enable 2FA."}


# ─────────────────────────────────────────────
# VERIFY AND CONFIRM ENABLE 2FA
# Step 2 — User submits the OTP to confirm enabling 2FA
# ─────────────────────────────────────────────
@router.post("/2fa/verify-enable")
async def verify_enable_2fa(
    data: Verify2FASchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check OTP is correct
    if user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check OTP has not expired
    otp_expires_at = user.get("otp_expires_at")
    if otp_expires_at:
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > otp_expires_at:
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")

    # Enable 2FA and clear the OTP
    await users_collection.update_one(
        {"email": current_user},
        {"$set": {
            "two_factor_enabled": True,
            "otp": None,
            "otp_expires_at": None,
            "security_updated_at": datetime.now(timezone.utc)
        }}
    )

    return {"message": "Two factor authentication enabled successfully"}


# ─────────────────────────────────────────────
# DISABLE TWO FACTOR AUTHENTICATION
# User submits their password to confirm disabling 2FA
# ─────────────────────────────────────────────
@router.post("/2fa/disable")
async def disable_2fa(
    data: Toggle2FASchema,
    current_user: str = Depends(get_current_user)
):
    from app.auth import verify_password

    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2FA must be enabled before it can be disabled
    if not user.get("two_factor_enabled", False):
        raise HTTPException(status_code=400, detail="Two factor authentication is not enabled")

    # Require password confirmation before disabling a security feature
    if user.get("password") and not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    await users_collection.update_one(
        {"email": current_user},
        {"$set": {
            "two_factor_enabled": False,
            "security_updated_at": datetime.now(timezone.utc)
        }}
    )

    return {"message": "Two factor authentication disabled successfully"}


# ─────────────────────────────────────────────
# TOGGLE LOGIN ALERTS
# User can turn login alert emails on or off
# ─────────────────────────────────────────────
@router.post("/login-alerts")
async def toggle_login_alerts(
    data: ToggleLoginAlertsSchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await users_collection.update_one(
        {"email": current_user},
        {"$set": {
            "login_alerts_enabled": data.enabled,
            "security_updated_at": datetime.now(timezone.utc)
        }}
    )

    status = "enabled" if data.enabled else "disabled"
    return {"message": f"Login alerts {status} successfully"}


# ─────────────────────────────────────────────
# SET AUTO LOCK
# User sets how many minutes before the session auto locks
# Flutter uses this to automatically log the user out after inactivity
# ─────────────────────────────────────────────
@router.post("/auto-lock")
async def set_auto_lock(
    data: SetAutoLockSchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await users_collection.update_one(
        {"email": current_user},
        {"$set": {
            "auto_lock_minutes": data.minutes,
            "security_updated_at": datetime.now(timezone.utc)
        }}
    )

    return {
        "message": f"Auto lock set to {data.minutes} minutes successfully",
        "auto_lock_minutes": data.minutes
    }