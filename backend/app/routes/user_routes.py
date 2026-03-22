# app/routes/user_routes.py
# AquaSense — User profile routes
# Kulith's user_routes.py ported from supabase-py → SQLAlchemy.
# All endpoint URLs, logic, and response shapes preserved exactly.
#
# Field mapping (supabase → SQLAlchemy User):
#   password            → password_hash
#   phone               → phone_encrypted  (stored encrypted, decrypted on read)
#   address             → address_encrypted (stored encrypted, decrypted on read)
#   two_factor_enabled  → two_fa_enabled
#   login_alerts_enabled → login_alerts

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import User
from schemas import UpdateProfileSchema
from app.utils.encryption import encrypt, decrypt

router = APIRouter(prefix="/user", tags=["User"])

WATER_SOURCES = [
    "Municipal Water Supply",
    "Well Water",
    "Rainwater",
    "Borehole",
    "River Water",
    "Spring Water",
    "Other"
]


# ─────────────────────────────────────────────
# GET PROFILE
# ─────────────────────────────────────────────

@router.get("/profile")
async def get_profile(
    current_user = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    return {
        "email":         current_user.email,
        "name":          current_user.name,
        # Phone encrypted — decrypt before sending to Flutter
        "phone":         decrypt(current_user.phone_encrypted)
                         if current_user.phone_encrypted else None,
        # Address encrypted — decrypt before sending to Flutter
        "address":       decrypt(current_user.address_encrypted)
                         if current_user.address_encrypted else None,
        "profile_picture": current_user.profile_picture,
        "auth_provider": current_user.auth_provider,
        "is_verified":   current_user.is_verified,
        "created_at":    current_user.created_at.isoformat() if current_user.created_at else None,
        # Security settings — note the renamed fields
        "two_factor_enabled":   current_user.two_fa_enabled,
        "login_alerts_enabled": current_user.login_alerts,
        "auto_lock_minutes":    current_user.auto_lock_minutes,
        # District
        "district":      current_user.district,
        # Device info
        "device_id":     current_user.device_id,
        "install_date":  current_user.install_date.isoformat() if current_user.install_date else None,
        # Water info
        "water_source":    current_user.water_source,
        "household_size":  current_user.household_size,
    }


# ─────────────────────────────────────────────
# UPDATE PROFILE
# ─────────────────────────────────────────────

@router.put("/update-profile")
async def update_profile(
    data:        UpdateProfileSchema,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    updated = False

    if data.name is not None:
        current_user.name = data.name
        updated = True

    if data.phone is not None:
        # Encrypt before storing
        current_user.phone_encrypted = encrypt(data.phone)
        updated = True

    if data.address is not None:
        # Encrypt before storing
        current_user.address_encrypted = encrypt(data.address)
        updated = True

    if data.profile_picture is not None:
        current_user.profile_picture = data.profile_picture
        updated = True

    if not updated:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    await db.commit()
    return {"message": "Profile updated successfully"}


# ─────────────────────────────────────────────
# REGISTER DEVICE
# ─────────────────────────────────────────────

@router.post("/register-device")
async def register_device(
    data:        dict,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    device_id = data.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID is required")

    current_user.device_id = device_id

    # Only set install date once — never overwrite it
    if not current_user.install_date:
        current_user.install_date = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message":      "Device registered successfully",
        "device_id":    device_id,
        "install_date": current_user.install_date.isoformat() if current_user.install_date else None,
    }


# ─────────────────────────────────────────────
# DELETE ACCOUNT
# ─────────────────────────────────────────────

@router.delete("/delete-account")
async def delete_account(
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    await db.delete(current_user)
    await db.commit()
    return {"message": "Account deleted successfully"}
