# app/auth.py
# Manual JWT authentication – no Firebase, no Supabase

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import User, RefreshToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Password ──────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Access token ──────────────────────────────────────────────────────────────
def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Refresh token ─────────────────────────────────────────────────────────────
def create_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash). Only hash is stored in DB."""
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


# ── FastAPI dependencies ──────────────────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    user_id = int(payload.get("sub", 0))
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

async def require_admin(current: User = Depends(get_current_user)) -> User:
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current
