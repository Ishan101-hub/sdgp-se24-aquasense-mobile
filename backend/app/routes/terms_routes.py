# app/routes/terms_routes.py
# AquaSense — Terms and conditions routes
# Kulith's terms_routes.py ported from supabase-py → SQLAlchemy.

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from schemas import TermsSchema

router = APIRouter(prefix="/terms", tags=["Terms"])


# ─────────────────────────────────────────────
# GET TERMS STATUS
# ─────────────────────────────────────────────

@router.get("/status")
async def get_terms_status(
    current_user = Depends(get_current_user),
):
    return {
        "terms_of_service": current_user.terms_of_service,
        "terms_accepted_at": current_user.terms_accepted_at.isoformat()
                             if current_user.terms_accepted_at else None,
        "terms_completed":  current_user.terms_completed,
    }


# ─────────────────────────────────────────────
# SAVE TERMS
# ─────────────────────────────────────────────

@router.post("/save")
async def save_terms(
    data:        TermsSchema,
    current_user = Depends(get_current_user),
    db:          AsyncSession = Depends(get_db),
):
    if not data.terms_of_service:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service to continue"
        )

    current_user.terms_of_service = True
    current_user.terms_accepted_at = datetime.now(timezone.utc)
    current_user.terms_completed   = True
    await db.commit()

    return {"message": "Terms and conditions saved successfully"}


# ─────────────────────────────────────────────
# CHECK TERMS
# ─────────────────────────────────────────────

@router.get("/check")
async def check_terms(
    current_user = Depends(get_current_user),
):
    return {
        "terms_completed":  current_user.terms_completed,
        "terms_accepted_at": current_user.terms_accepted_at.isoformat()
                             if current_user.terms_accepted_at else None,
    }
