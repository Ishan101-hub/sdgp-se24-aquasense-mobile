from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# This tells FastAPI where to get the token from
# Flutter sends the token in the Authorization header as Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# bcrypt is used to hash passwords before storing them
# and to verify passwords during login
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # Converts plain text password to a secure hash
    # Example: "TestPass123!" → "$2b$12$..."
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Checks if the plain text password matches the stored hash
    # Returns True if they match, False if they do not
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    # Creates a short lived token used to access protected routes
    # Expires after ACCESS_TOKEN_EXPIRE_MINUTES (default 30 minutes)
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    # Creates a long lived token used to get a new access token
    # Expires after 7 days
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    # This function runs before every protected route
    # It checks the token is valid and not blacklisted
    from app.database import blacklisted_tokens_collection

    # First check if the token has been blacklisted
    # This happens when the user logs out
    # Even if the token has not expired yet it will be rejected
    blacklisted = await blacklisted_tokens_collection.find_one({"token": token})
    if blacklisted:
        raise HTTPException(
            status_code=401,
            detail="Token has been invalidated. Please login again"
        )

    # Now verify the token is valid and not expired
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")

        # Make sure the token has an email and is an access token
        # Refresh tokens should never be used to access protected routes
        if email is None or token_type != "access":
            raise HTTPException(
                status_code=401,
                detail="Invalid token. Please login again"
            )

        return email

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please login again"
        )