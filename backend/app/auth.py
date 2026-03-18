# auth.py
# AquaSense — JWT authentication utilities
#
# Kulith's authentication logic adapted for this server's SQLAlchemy/Supabase stack.
#
# Key design decision:
#   Kulith's get_current_user() returns an email string.
#   This server's analytics_router, device_router, and mobile_router all call
#   current_user.id in every ownership check.
#   So get_current_user() here returns the full User ORM object — same as before —
#   but uses Kulith's token structure (sub = email, type = "access").
#
# Token structure (Kulith's):
#   Access token:  {"sub": email, "type": "access",  "exp": ...}
#   Refresh token: {"sub": email, "type": "refresh", "exp": ...}
#
# Blacklist: stored in blacklisted_tokens table (PostgreSQL) instead of MongoDB.

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db

# Flutter sends the token in the Authorization header as Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# bcrypt is used to hash passwords before storing and to verify during login
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Converts plain text password to a secure bcrypt hash."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Returns True if plain_password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── Access token ──────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """
    Creates a short-lived access token.
    Kulith's structure: {"sub": email, "type": "access", "exp": ...}
    Expires after ACCESS_TOKEN_EXPIRE_MINUTES (default 30 minutes).
    """
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ── Refresh token ─────────────────────────────────────────────────────────────

def create_refresh_token(data: dict) -> str:
    """
    Creates a long-lived refresh token.
    Kulith's structure: {"sub": email, "type": "refresh", "exp": ...}
    Expires after 7 days.
    """
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_user(
    token: str          = Depends(oauth2_scheme),
    db:    AsyncSession = Depends(get_db),
):
    """
    Dependency that runs before every protected route.
    Returns the full User ORM object so all existing routers can use current_user.id.

    Steps (Kulith's logic):
      1. Check token is not blacklisted (logout invalidation)
      2. Decode and verify the JWT
      3. Confirm token type is "access" (not "refresh")
      4. Load and return the User row from PostgreSQL
    """
    from models import User, BlacklistedToken

    # Step 1: reject blacklisted tokens (happens when user logs out)
    blacklisted = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.token == token)
    )
    if blacklisted.scalar_one_or_none():
        raise HTTPException(
            status_code=401,
            detail="Token has been invalidated. Please login again"
        )

    # Step 2 + 3: verify JWT and check token type
    try:
        payload    = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        token_type = payload.get("type")

        # Refresh tokens must never be used to access protected routes
        if not email or token_type != "access":
            raise HTTPException(
                status_code=401,
                detail="Invalid token. Please login again"
            )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please login again"
        )

    # Step 4: load the User ORM object (needed for current_user.id in all routers)
    result = await db.execute(
        select(User).where(User.email == email, User.is_verified == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found or not verified. Please login again"
        )
    return user


async def require_admin(current_user=Depends(get_current_user)):
    """Blocks non-admin users from admin-only endpoints."""
    if getattr(current_user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

