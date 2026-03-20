from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone, timedelta
from app.database import supabase
from app.auth import get_current_user
from app.schemas import (
    Toggle2FASchema, Verify2FASchema,
    ToggleLoginAlertsSchema, SetAutoLockSchema
)
from app.email_utils import generate_otp, send_email

router = APIRouter(prefix="/security", tags=["Security"])
OTP_EXPIRE_MINUTES = 10


# ─────────────────────────────────────────────
# GET SECURITY SETTINGS
# ─────────────────────────────────────────────
@router.get("/settings")
async def get_security_settings(current_user: str = Depends(get_current_user)):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "two_factor_enabled": user.get("two_factor_enabled", False),
        "login_alerts_enabled": user.get("login_alerts_enabled", True),
        "auto_lock_minutes": user.get("auto_lock_minutes", 30),
    }


# ─────────────────────────────────────────────
# ENABLE 2FA
# ─────────────────────────────────────────────
@router.post("/2fa/enable")
async def enable_2fa(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("two_factor_enabled", False):
        raise HTTPException(status_code=400, detail="Two factor authentication is already enabled")

    otp = generate_otp()
    otp_expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    ).isoformat()

    supabase.table("users").update({
        "otp": otp,
        "otp_expires_at": otp_expires_at
    }).eq("email", current_user).execute()

    background_tasks.add_task(send_email, current_user, otp, "2fa")
    return {"message": "OTP sent to your email. Please verify to enable 2FA."}


# ─────────────────────────────────────────────
# VERIFY ENABLE 2FA
# ─────────────────────────────────────────────
@router.post("/2fa/verify-enable")
async def verify_enable_2fa(
    data: Verify2FASchema,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
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

    supabase.table("users").update({
        "two_factor_enabled": True,
        "otp": None,
        "otp_expires_at": None,
        "security_updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("email", current_user).execute()

    return {"message": "Two factor authentication enabled successfully"}


# ─────────────────────────────────────────────
# DISABLE 2FA
# ─────────────────────────────────────────────
@router.post("/2fa/disable")
async def disable_2fa(
    data: Toggle2FASchema,
    current_user: str = Depends(get_current_user)
):
    from app.auth import verify_password

    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.get("two_factor_enabled", False):
        raise HTTPException(status_code=400, detail="Two factor authentication is not enabled")
    if user.get("password") and not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    supabase.table("users").update({
        "two_factor_enabled": False,
        "security_updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("email", current_user).execute()

    return {"message": "Two factor authentication disabled successfully"}


# ─────────────────────────────────────────────
# TOGGLE LOGIN ALERTS
# ─────────────────────────────────────────────
@router.post("/login-alerts")
async def toggle_login_alerts(
    data: ToggleLoginAlertsSchema,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    supabase.table("users").update({
        "login_alerts_enabled": data.enabled,
        "security_updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("email", current_user).execute()

    status = "enabled" if data.enabled else "disabled"
    return {"message": f"Login alerts {status} successfully"}


# ─────────────────────────────────────────────
# SET AUTO LOCK
# ─────────────────────────────────────────────
@router.post("/auto-lock")
async def set_auto_lock(
    data: SetAutoLockSchema,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    supabase.table("users").update({
        "auto_lock_minutes": data.minutes,
        "security_updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("email", current_user).execute()

    return {
        "message": f"Auto lock set to {data.minutes} minutes successfully",
        "auto_lock_minutes": data.minutes
    }