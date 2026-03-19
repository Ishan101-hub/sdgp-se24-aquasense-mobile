from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.database import users_collection
from app.auth import get_current_user
from app.schemas import TermsSchema

router = APIRouter(prefix="/terms", tags=["Terms"])


# ─────────────────────────────────────────────
# GET TERMS STATUS
# Returns the current state of the terms checkbox
# Flutter uses this to show whether the box is already checked
# ─────────────────────────────────────────────
@router.get("/status")
async def get_terms_status(current_user: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "terms_of_service": user.get("terms_of_service", False),
        "terms_accepted_at": user.get("terms_accepted_at", None),
        "terms_completed": user.get("terms_completed", False)
    }


# ─────────────────────────────────────────────
# SAVE TERMS
# Saves the terms checkbox state when user clicks Confirm and Save
# Only terms_of_service is required
# ─────────────────────────────────────────────
@router.post("/save")
async def save_terms(
    data: TermsSchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only one required checkbox — terms of service
    if not data.terms_of_service:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service to continue"
        )

    # Save to database
    await users_collection.update_one(
        {"email": current_user},
        {"$set": {
            "terms_of_service": data.terms_of_service,
            # Record when the user accepted
            "terms_accepted_at": datetime.now(timezone.utc),
            # Mark as completed so Flutter skips this page next login
            "terms_completed": True
        }}
    )

    return {"message": "Terms and conditions saved successfully"}


# ─────────────────────────────────────────────
# CHECK IF TERMS ARE COMPLETED
# Flutter calls this after login to decide whether to show
# the terms page or go directly to the home screen
# ─────────────────────────────────────────────
@router.get("/check")
async def check_terms(current_user: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        # Flutter checks this — if False show terms page, if True go to home
        "terms_completed": user.get("terms_completed", False),
        "terms_accepted_at": user.get("terms_accepted_at", None)
    }