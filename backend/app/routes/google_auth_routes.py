from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx
from app.database import users_collection
from app.auth import create_access_token, create_refresh_token
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Google Auth"])

# Google OAuth endpoints — these are fixed URLs provided by Google
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# ─────────────────────────────────────────────
# STEP 1: GOOGLE LOGIN
# User hits this endpoint and gets redirected to Google login page
# ─────────────────────────────────────────────
@router.get("/google/login")
async def google_login():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline"
    }

    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    google_auth_url = f"{GOOGLE_AUTH_URL}?{query_string}"

    return RedirectResponse(url=google_auth_url)


# ─────────────────────────────────────────────
# STEP 2: GOOGLE CALLBACK
# Google redirects here after user approves login
# We create or login the user and return our JWT tokens
# ─────────────────────────────────────────────
@router.get("/google/callback")
async def google_callback(code: str):

    # Exchange the code Google gave us for an access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI
            }
        )

    token_data = token_response.json()

    if "access_token" not in token_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to get access token from Google. Please try again"
        )

    google_access_token = token_data["access_token"]

    # Use the Google access token to get the user profile info
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"}
        )

    userinfo = userinfo_response.json()

    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Could not retrieve email from Google account"
        )

    existing_user = await users_collection.find_one({"email": email})

    if existing_user:
        # User already exists — just log them in
        # Mark as verified since Google confirmed their email
        if not existing_user.get("is_verified", False):
            await users_collection.update_one(
                {"email": email},
                {"$set": {"is_verified": True}}
            )
    else:
        # Brand new user — create account automatically
        # password is None — they can set one later via forgot password
        # to enable normal login as well
        await users_collection.insert_one({
            "email": email,
            "name": name,
            "password": None,
            "phone": None,
            "is_verified": True,
            "otp": None,
            "otp_expires_at": None,
            "address": None,
            "profile_picture": picture,
            "auth_provider": "google",
            "created_at": datetime.now(timezone.utc)
        })

    # Create our own JWT tokens
    access_token = create_access_token({"sub": email})
    refresh_token = create_refresh_token({"sub": email})

    # Save the refresh token so we can invalidate it on logout
    await users_collection.update_one(
        {"email": email},
        {"$set": {"refresh_token": refresh_token}}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "email": email,
        "name": name,
        "profile_picture": picture
    }