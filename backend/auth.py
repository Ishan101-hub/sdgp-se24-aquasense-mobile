# auth.py
# AquaSense — JWT authentication utilities
# Updated for Python 3.13 compatibility using native bcrypt

from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    """
    Hashes a password using the native bcrypt library.
    Bypasses the passlib ValueError bug in Python 3.13.
    """
    # Truncate to 72 bytes (bcrypt limit) and encode to bytes
    pwd_bytes = password[:72].encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # Return as string for database storage
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifies a plain password against a stored hash.
    """
    try:
        if not plain or not hashed:
            return False
        pwd_bytes = plain[:72].encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    """{"sub": email, "type": "access"} — expires in ACCESS_TOKEN_EXPIRE_MINUTES."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """{"sub": email, "type": "refresh"} — expires in 7 days."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    from models import User, BlacklistedToken

    # 1. Rejects blacklisted tokens (post-logout)
    bl = await db.execute(
        select(BlacklistedToken).where(BlacklistedToken.token == token)
    )
    if bl.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="Token invalidated. Please login again")

    # 2. Decode JWT
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        token_type = payload.get("type")

        if not email or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Session expired. Please login again")

    # 3. Load full User ORM object
    result = await db.execute(
        select(User).where(User.email == email, User.is_verified == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or not verified.")
    return user