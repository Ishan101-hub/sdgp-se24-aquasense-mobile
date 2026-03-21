# app/routes/security_routes.py
# AquaSense — Security settings routes
# Kulith's security_routes.py ported from supabase-py → SQLAlchemy.
#
# Field mapping:
#   two_factor_enabled   → User.two_fa_enabled
#   login_alerts_enabled → User.login_alerts

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, verify_password
from database import get_db
from email_utils import generate_otp, send_email
from schemas import (
    Toggle2FASchema, Verify2FASchema,
    ToggleLoginAlertsSchema, SetAutoLockSchema,
)

router = APIRouter(prefix="/security", tags=["Security"])
OTP_EXPIRE_MINUTES = 10


# ─────────────────────────────────────────────
# GET SECURITY SETTINGS
# ─────────────────────────────────────────────

@router.get("/settings")
async def get_security_settings(
    current_user = Depends(get_current_user),
):
    return {
        # Response keys match Kulith's original so Flutter doesn't need changes
        "two_factor_enabled":   current_user.two_fa_enabled,
        "login_alerts_enabled": current_user.login_alerts,
        "auto_lock_minutes":    current_user.auto_lock_minutes,
    }


# ─────────────────────────────────────────────
# ENABLE 2FA
# ─────────────────────────────────────────────

@router.post("/2fa/enable")
async def enable_2fa(
    background_tasks: BackgroundTasks,
    current_user      = Depends(get_current_user),
    db:               AsyncSession = Depends(get_db),
):
    if current_user.two_fa_enabled:
        raise HTTPException(status_code=400,
                            detail="Two factor authentication is already enabled")

    otp                     = generate_otp()
    current_user.otp        = otp
    current_user.otp_expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    )
    current_user.otp_type   = "2fa"
    await db.commit()

    background_tasks.add_task(send_email, current_user.email, otp, "2fa")
    return {"message": "OTP sent to your email. Please verify to enable 2FA."}


# ─────────────────────────────────────────────
# VERIFY ENABLE 2FA
# ─────────────────────────────────────────────

@router.post("/2fa/verify-enable")
async def verify_enable_2fa(
    data:        Verify2FASchema,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    if current_user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if current_user.otp_expires_at and datetime.now(timezone.utc) > current_user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")

    current_user.two_fa_enabled  = True
    current_user.otp             = None
    current_user.otp_expires_at  = None
    current_user.otp_type        = None
    await db.commit()

    return {"message": "Two factor authentication enabled successfully"}


# ─────────────────────────────────────────────
# DISABLE 2FA
# ─────────────────────────────────────────────

@router.post("/2fa/disable")
async def disable_2fa(
    data:        Toggle2FASchema,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    if not current_user.two_fa_enabled:
        raise HTTPException(status_code=400,
                            detail="Two factor authentication is not enabled")
    if current_user.password_hash and not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    current_user.two_fa_enabled = False
    await db.commit()

    return {"message": "Two factor authentication disabled successfully"}


# ─────────────────────────────────────────────
# TOGGLE LOGIN ALERTS
# ─────────────────────────────────────────────

@router.post("/login-alerts")
async def toggle_login_alerts(
    data:        ToggleLoginAlertsSchema,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    current_user.login_alerts = data.enabled
    await db.commit()

    status = "enabled" if data.enabled else "disabled"
    return {"message": f"Login alerts {status} successfully"}


# ─────────────────────────────────────────────
# SET AUTO LOCK
# ─────────────────────────────────────────────

@router.post("/auto-lock")
async def set_auto_lock(
    data:        SetAutoLockSchema,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    current_user.auto_lock_minutes = data.minutes
    await db.commit()

    return {
        "message":          f"Auto lock set to {data.minutes} minutes successfully",
        "auto_lock_minutes": data.minutes,
    }
