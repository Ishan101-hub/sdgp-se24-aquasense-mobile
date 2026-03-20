from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.database import supabase
from app.auth import get_current_user
from app.schemas import TermsSchema

router = APIRouter(prefix="/terms", tags=["Terms"])


# ─────────────────────────────────────────────
# GET TERMS STATUS
# ─────────────────────────────────────────────
@router.get("/status")
async def get_terms_status(current_user: str = Depends(get_current_user)):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "terms_of_service": user.get("terms_of_service", False),
        "terms_accepted_at": user.get("terms_accepted_at", None),
        "terms_completed": user.get("terms_completed", False)
    }


# ─────────────────────────────────────────────
# SAVE TERMS
# ─────────────────────────────────────────────
@router.post("/save")
async def save_terms(
    data: TermsSchema,
    current_user: str = Depends(get_current_user)
):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    if not data.terms_of_service:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service to continue"
        )

    supabase.table("users").update({
        "terms_of_service": data.terms_of_service,
        "terms_accepted_at": datetime.now(timezone.utc).isoformat(),
        "terms_completed": True
    }).eq("email", current_user).execute()

    return {"message": "Terms and conditions saved successfully"}


# ─────────────────────────────────────────────
# CHECK TERMS
# ─────────────────────────────────────────────
@router.get("/check")
async def check_terms(current_user: str = Depends(get_current_user)):
    result = supabase.table("users").select("*").eq("email", current_user).execute()
    user = result.data[0] if result.data else None

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "terms_completed": user.get("terms_completed", False),
        "terms_accepted_at": user.get("terms_accepted_at", None)
    }