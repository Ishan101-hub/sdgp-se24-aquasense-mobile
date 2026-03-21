# app/routes/district_routes.py
# AquaSense — District selection routes
# Kulith's district_routes.py ported from supabase-py → SQLAlchemy.

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from schemas import DistrictSchema

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
        "total":     len(SRI_LANKA_DISTRICTS),
    }


# ─────────────────────────────────────────────
# GET MY DISTRICT
# ─────────────────────────────────────────────

@router.get("/my-district")
async def get_my_district(
    current_user = Depends(get_current_user),
):
    return {"district": current_user.district}


# ─────────────────────────────────────────────
# SAVE DISTRICT
# ─────────────────────────────────────────────

@router.post("/save")
async def save_district(
    data:        DistrictSchema,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    if data.district not in SRI_LANKA_DISTRICTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid district. Please select a valid Sri Lanka district"
        )

    current_user.district = data.district
    await db.commit()

    return {
        "message":  "District saved successfully",
        "district": data.district,
    }
