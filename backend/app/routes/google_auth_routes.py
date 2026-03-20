from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx
from app.database import supabase
from app.auth import create_access_token, create_refresh_token
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Google Auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# ─────────────────────────────────────────────
# GOOGLE LOGIN
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
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{query_string}")


# ─────────────────────────────────────────────
# GOOGLE CALLBACK
# ─────────────────────────────────────────────
@router.get("/google/callback")
async def google_callback(code: str):
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

    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
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

    existing = supabase.table("users").select("*").eq("email", email).execute()

    if existing.data:
        # User exists — just log them in
        if not existing.data[0].get("is_verified", False):
            supabase.table("users").update({
                "is_verified": True
            }).eq("email", email).execute()
    else:
        # New user — create account automatically
        supabase.table("users").insert({
            "email": email,
            "name": name,
            "password": None,
            "phone": None,
            "is_verified": True,
            "profile_picture": picture,
            "auth_provider": "google",
            "two_factor_enabled": False,
            "login_alerts_enabled": True,
            "auto_lock_minutes": 30,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

    access_token = create_access_token({"sub": email})
    refresh_token = create_refresh_token({"sub": email})

    supabase.table("users").update({
        "refresh_token": refresh_token
    }).eq("email", email).execute()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "email": email,
        "name": name,
        "profile_picture": picture
    }