from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.auth import get_current_user
from app.schemas import UpdateProfileSchema
from app.utils.encryption import encrypt, decrypt
from datetime import datetime, timezone

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
async def get_profile(current_user: str = Depends(get_current_user)):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": user["email"],
        "name": user.get("name"),
        # Phone is stored as plain text — return directly
        "phone": user.get("phone"),
        # Address is stored encrypted — decrypt before sending to Flutter
        "address": decrypt(user["address"]) if user.get("address") else None,
        "profile_picture": user.get("profile_picture"),
        "auth_provider": user.get("auth_provider", "local"),
        "is_verified": user.get("is_verified", False),
        "created_at": user.get("created_at"),
        # Security settings
        "two_factor_enabled": user.get("two_factor_enabled", False),
        "login_alerts_enabled": user.get("login_alerts_enabled", True),
        "auto_lock_minutes": user.get("auto_lock_minutes", 30),
        # District
        "district": user.get("district", None),
        # Device info
        "device_id": user.get("device_id", None),
        "install_date": user.get("install_date", None),
        # Water info
        "water_source": user.get("water_source", None),
        "household_size": user.get("household_size", None),
    }


# ─────────────────────────────────────────────
# UPDATE PROFILE
# ─────────────────────────────────────────────
@router.put("/update-profile")
async def update_profile(
    data: UpdateProfileSchema,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {}

    if data.name is not None:
        update_data["name"] = data.name

    if data.phone is not None:
        # Phone stored as plain text — used for login searches
        update_data["phone"] = data.phone

    if data.address is not None:
        # Address encrypted before saving
        update_data["address"] = encrypt(data.address)

    if data.profile_picture is not None:
        update_data["profile_picture"] = data.profile_picture

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    supabase.table("users").update(update_data).eq("email", current_user).execute()

    return {"message": "Profile updated successfully"}


# ─────────────────────────────────────────────
# REGISTER DEVICE
# ─────────────────────────────────────────────
@router.post("/register-device")
async def register_device(
    data: dict,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    device_id = data.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID is required")

    update_data = {"device_id": device_id}

    # Only set install date once — never overwrite it
    if not user.get("install_date"):
        update_data["install_date"] = datetime.now(timezone.utc).isoformat()

    supabase.table("users").update(update_data).eq("email", current_user).execute()

    return {
        "message": "Device registered successfully",
        "device_id": device_id,
        "install_date": user.get("install_date")
    }


# ─────────────────────────────────────────────
# GET WATER SOURCES
# ─────────────────────────────────────────────
@router.get("/water-sources")
async def get_water_sources():
    return {"water_sources": WATER_SOURCES}


# ─────────────────────────────────────────────
# DELETE ACCOUNT
# ─────────────────────────────────────────────
@router.delete("/delete-account")
async def delete_account(current_user: str = Depends(get_current_user)):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    supabase.table("users").delete().eq("email", current_user).execute()

    return {"message": "Account deleted successfully"}