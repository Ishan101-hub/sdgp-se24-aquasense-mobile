from typing import Optional
from pydantic import BaseModel, EmailStr

# This represents what a user looks like in our database
# It is not used for request validation — that is what schemas.py is for
# This is just a reference model that describes the user document structure
class UserModel(BaseModel):
    email: EmailStr          # must be a valid email format e.g. user@gmail.com
    password: str            # stored as a bcrypt hash, never plain text
    is_verified: bool = False  # starts as False until the user verifies their email
    otp: Optional[str] = None          # the 6 digit OTP sent to their email
    otp_expires_at: Optional[str] = None  # OTP becomes invalid after 10 minutes