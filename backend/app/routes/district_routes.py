from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.auth import get_current_user
from app.schemas import DistrictSchema

router = APIRouter(prefix="/district", tags=["District"])

SRI_LANKA_DISTRICTS = [
    "Ampara", "Anuradhapura", "Badulla", "Batticaloa",
    "Colombo", "Galle", "Gampaha", "Hambantota",
    "Jaffna", "Kalutara", "Kandy", "Kegalle",
    "Kilinochchi", "Kurunegala", "Mannar", "Matale",
    "Matara", "Monaragala", "Mullaitivu", "Nuwara Eliya",
    "Polonnaruwa", "Puttalam", "Ratnapura", "Trincomalee",
    "Vavuniya"
]


# ─────────────────────────────────────────────
# GET ALL DISTRICTS
# ─────────────────────────────────────────────
@router.get("/all")
async def get_all_districts():
    return {
        "districts": SRI_LANKA_DISTRICTS,
        "total": len(SRI_LANKA_DISTRICTS)
    }


# ─────────────────────────────────────────────
# GET MY DISTRICT
# ─────────────────────────────────────────────
@router.get("/my-district")
async def get_my_district(current_user: str = Depends(get_current_user)):
    result = supabase.table("users").select("district").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"district": user.get("district", None)}


# ─────────────────────────────────────────────
# SAVE DISTRICT
# ─────────────────────────────────────────────
@router.post("/save")
async def save_district(
    data: DistrictSchema,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    if data.district not in SRI_LANKA_DISTRICTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid district. Please select a valid Sri Lanka district"
        )

    supabase.table("users").update({
        "district": data.district
    }).eq("email", current_user).execute()

    return {
        "message": "District saved successfully",
        "district": data.district
    }