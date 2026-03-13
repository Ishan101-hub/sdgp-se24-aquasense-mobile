from fastapi import APIRouter, HTTPException, Depends
from app.database import users_collection
from app.auth import get_current_user
from app.schemas import DistrictSchema

router = APIRouter(prefix="/district", tags=["District"])

# All 25 districts in Sri Lanka
# These are the only valid values the user can select
SRI_LANKA_DISTRICTS = [
    "Ampara",
    "Anuradhapura",
    "Badulla",
    "Batticaloa",
    "Colombo",
    "Galle",
    "Gampaha",
    "Hambantota",
    "Jaffna",
    "Kalutara",
    "Kandy",
    "Kegalle",
    "Kilinochchi",
    "Kurunegala",
    "Mannar",
    "Matale",
    "Matara",
    "Monaragala",
    "Mullaitivu",
    "Nuwara Eliya",
    "Polonnaruwa",
    "Puttalam",
    "Ratnapura",
    "Trincomalee",
    "Vavuniya"
]


# ─────────────────────────────────────────────
# GET ALL DISTRICTS
# Returns the full list of 25 Sri Lanka districts
# Flutter uses this to populate the dropdown or list
# No login required — this is public data
# ─────────────────────────────────────────────
@router.get("/all")
async def get_all_districts():
    return {
        "districts": SRI_LANKA_DISTRICTS,
        "total": len(SRI_LANKA_DISTRICTS)
    }


# ─────────────────────────────────────────────
# GET USER DISTRICT
# Returns the currently selected district for the logged in user
# Flutter uses this to show which district is already selected
# ─────────────────────────────────────────────
@router.get("/my-district")
async def get_my_district(current_user: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return the selected district
    # If no district has been selected yet return null
    return {
        "district": user.get("district", None)
    }


# ─────────────────────────────────────────────
# SAVE USER DISTRICT
# Saves the selected district for the logged in user
# Flutter calls this when user selects a district
# ─────────────────────────────────────────────
@router.post("/save")
async def save_district(
    data: DistrictSchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate that the selected district is one of the 25 valid districts
    # This prevents someone from sending a fake district name
    if data.district not in SRI_LANKA_DISTRICTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid district. Please select a valid Sri Lanka district"
        )

    # Save the district to the user document in MongoDB
    await users_collection.update_one(
        {"email": current_user},
        {"$set": {"district": data.district}}
    )

    return {
        "message": "District saved successfully",
        "district": data.district
    }