# auth.py
# AquaSense — JWT authentication utilities
#
# Uses Kulith's token structure: {"sub": email, "type": "access"}
# and his blacklist-based logout pattern.
#
# BRIDGE DESIGN:
#   Kulith's get_current_user() returns an email string.
#   Every IoT router uses current_user.id for ownership checks.
#   This version returns the full User ORM object so both systems work.

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """{"sub": email, "type": "access"} — expires in ACCESS_TOKEN_EXPIRE_MINUTES."""
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """{"sub": email, "type": "refresh"} — expires in 7 days."""
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(
    token: str          = Depends(oauth2_scheme),
    db:    AsyncSession = Depends(get_db),
):
    """
    1. Rejects blacklisted tokens (post-logout)
    2. Decodes JWT, confirms type == "access"
    3. Loads and returns the full User ORM object
       → current_user.id works in all IoT routes unchanged
    """
    from models import User, BlacklistedToken

    bl = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.token == token)
    )
    if bl.scalar_one_or_none():
        raise HTTPException(status_code=401,
                            detail="Token has been invalidated. Please login again")

    try:
        payload    = jwt.decode(token, settings.JWT_SECRET,
                                algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        token_type = payload.get("type")

        if not email or token_type != "access":
            raise HTTPException(status_code=401,
                                detail="Invalid token. Please login again")
    except JWTError:
        raise HTTPException(status_code=401,
                            detail="Invalid or expired token. Please login again")

    result = await db.execute(
        select(User).where(User.email == email, User.is_verified == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401,
                            detail="User not found or not verified. Please login again")
    return user
