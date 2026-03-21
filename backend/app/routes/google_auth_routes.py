# app/routes/google_auth_routes.py
# AquaSense — Google OAuth routes
# Kulith's google_auth_routes.py ported from supabase-py → SQLAlchemy.

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_access_token, create_refresh_token
from config import settings
from database import AsyncSessionLocal
from models import User

router = APIRouter(prefix="/auth", tags=["Google Auth"])

GOOGLE_AUTH_URL      = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL  = "https://www.googleapis.com/oauth2/v2/userinfo"


# ─────────────────────────────────────────────
# GOOGLE LOGIN
# ─────────────────────────────────────────────

@router.get("/google/login")
async def google_login():
    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{query_string}")


# ─────────────────────────────────────────────
# GOOGLE CALLBACK
# ─────────────────────────────────────────────

@router.get("/google/callback")
async def google_callback(code: str):
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code":          code,
                "grant_type":    "authorization_code",
                "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
            }
        )

    token_data = token_response.json()
    if "access_token" not in token_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to get access token from Google. Please try again"
        )

    # Fetch user info from Google
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )

    userinfo = userinfo_response.json()
    email    = userinfo.get("email")
    name     = userinfo.get("name")
    picture  = userinfo.get("picture")

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Could not retrieve email from Google account"
        )

    async with AsyncSessionLocal() as db:
        result   = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            # User exists — ensure they are verified
            if not existing.is_verified:
                existing.is_verified = True
                await db.commit()
        else:
            # New user — create account automatically
            new_user = User(
                email           = email,
                name            = name,
                password_hash   = None,       # no password for Google users
                is_verified     = True,
                auth_provider   = "google",
                profile_picture = picture,
                two_fa_enabled  = False,
                login_alerts    = True,
                auto_lock_minutes = 30,
            )
            db.add(new_user)
            await db.commit()

    access_token  = create_access_token({"sub": email})
    refresh_token = create_refresh_token({"sub": email})

    return {
        "access_token":   access_token,
        "refresh_token":  refresh_token,
        "token_type":     "bearer",
        "email":          email,
        "name":           name,
        "profile_picture": picture,
    }
