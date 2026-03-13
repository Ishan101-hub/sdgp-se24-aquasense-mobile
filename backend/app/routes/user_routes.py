from fastapi import APIRouter, HTTPException, Depends
from app.database import users_collection
from app.auth import get_current_user
from app.schemas import UpdateProfileSchema
from app.utils.encryption import encrypt, decrypt

router = APIRouter(prefix="/user", tags=["User"])


# ─────────────────────────────────────────────
# GET PROFILE
# Returns the logged in user's profile data
# Address is decrypted before being sent to Flutter
# Phone is plain text — no decryption needed
# District is returned so Flutter can show the selected district
# ─────────────────────────────────────────────
@router.get("/profile")
async def get_profile(current_user: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": user["email"],
        "name": user.get("name"),

        # Phone is stored as plain text — return directly
        "phone": user.get("phone"),

        # Address is stored encrypted in MongoDB
        # Decrypt it here before sending to Flutter
        "address": decrypt(user["address"]) if user.get("address") else None,

        "profile_picture": user.get("profile_picture"),
        "auth_provider": user.get("auth_provider", "local"),
        "is_verified": user.get("is_verified", False),
        "created_at": user.get("created_at"),

        # Security settings — Flutter uses these to show the current
        # state of each toggle on the security page
        "two_factor_enabled": user.get("two_factor_enabled", False),
        "login_alerts_enabled": user.get("login_alerts_enabled", True),
        "auto_lock_minutes": user.get("auto_lock_minutes", 30),

        # District — Flutter uses this to show the currently selected
        # district on the home page dropdown
        # Returns null if the user has not selected a district yet
        "district": user.get("district", None),
    }


# ─────────────────────────────────────────────
# UPDATE PROFILE
# Allows the logged in user to update their profile fields
# All fields are optional — they can update just one or all at once
# Only address is encrypted — phone is stored as plain text
# ─────────────────────────────────────────────
@router.put("/update-profile")
async def update_profile(
    data: UpdateProfileSchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build the update object with only the fields that were provided
    # Fields that are None are skipped — we do not overwrite existing data with None
    update_data = {}

    if data.name is not None:
        # Name is stored as plain text — no encryption needed
        update_data["name"] = data.name

    if data.phone is not None:
        # Phone is stored as plain text — no encryption
        # This is intentional because phone is used for login searches
        # Encrypting it would make login by phone impossible
        update_data["phone"] = data.phone

    if data.address is not None:
        # Address is encrypted before saving to MongoDB
        # Address is never used for searching so encryption is safe here
        update_data["address"] = encrypt(data.address)

    if data.profile_picture is not None:
        # Profile picture is a URL — no encryption needed
        update_data["profile_picture"] = data.profile_picture

    # If nothing was provided return an error
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    await users_collection.update_one(
        {"email": current_user},
        {"$set": update_data}
    )

    return {"message": "Profile updated successfully"}


# ─────────────────────────────────────────────
# DELETE ACCOUNT
# Permanently deletes the logged in user's account
# This cannot be undone
# ─────────────────────────────────────────────
@router.delete("/delete-account")
async def delete_account(
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Permanently delete the user document from MongoDB
    await users_collection.delete_one({"email": current_user})

    return {"message": "Account deleted successfully"}