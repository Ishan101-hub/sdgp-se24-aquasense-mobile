from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.database import users_collection
from app.auth import get_current_user
from app.schemas import TermsSchema

router = APIRouter(prefix="/terms", tags=["Terms"])


# ─────────────────────────────────────────────
# GET TERMS STATUS
# Returns the current state of all checkboxes for the logged in user
# Flutter uses this to show which boxes are already checked
# ─────────────────────────────────────────────
@router.get("/status")
async def get_terms_status(current_user: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return the current state of each checkbox
    # If the user has never seen this page all values will be False
    return {
        "terms_of_service": user.get("terms_of_service", False),
        "privacy_policy": user.get("privacy_policy", False),
        "iot_data_collection": user.get("iot_data_collection", False),
        "cookie_policy": user.get("cookie_policy", False),
        "tips_and_updates": user.get("tips_and_updates", False),
        "terms_accepted_at": user.get("terms_accepted_at", None),
        "terms_completed": user.get("terms_completed", False)
    }


# ─────────────────────────────────────────────
# SAVE TERMS
# Saves the state of all checkboxes when user clicks Confirm and Save
# Required checkboxes must all be True or the request is rejected
# ─────────────────────────────────────────────
@router.post("/save")
async def save_terms(
    data: TermsSchema,
    current_user: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # These three are required — shown with * in the Flutter UI
    # If any of them are False we reject the request
    if not data.terms_of_service:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service to continue"
        )
    if not data.privacy_policy:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Privacy Policy to continue"
        )
    if not data.iot_data_collection:
        raise HTTPException(
            status_code=400,
            detail="You must consent to IoT Data Collection to continue"
        )

    # Save all checkbox states to the database
    # Optional checkboxes are saved as whatever the user selected
    await users_collection.update_one(
        {"email": current_user},
        {"$set": {
            # Required checkboxes
            "terms_of_service": data.terms_of_service,
            "privacy_policy": data.privacy_policy,
            "iot_data_collection": data.iot_data_collection,
            # Optional checkboxes
            "cookie_policy": data.cookie_policy,
            "tips_and_updates": data.tips_and_updates,
            # Record when the user accepted the terms
            "terms_accepted_at": datetime.now(timezone.utc),
            # Mark terms as completed so Flutter can skip this page on next login
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

    terms_completed = user.get("terms_completed", False)

    return {
        # Flutter checks this — if False show terms page, if True go to home
        "terms_completed": terms_completed,
        "terms_accepted_at": user.get("terms_accepted_at", None)
    }