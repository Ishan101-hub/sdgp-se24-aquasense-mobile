from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re

# Common weak passwords that are blocked
# These are the most frequently used passwords that hackers try first
COMMON_PASSWORDS = [
    "password", "password123", "123456", "12345678",
    "qwerty", "abc123", "letmein", "welcome",
    "monkey", "dragon", "master", "sunshine"
]

# Characters that are dangerous in a MongoDB context
# For example $gt, $ne are MongoDB operators — if someone injects these
# they could manipulate database queries and access data they should not
DANGEROUS_CHARACTERS = ["$", "{", "}", "<", ">", "\\", "|"]


def strip_html_tags(v: str) -> str:
    # Removes HTML tags like <script>alert('hacked')</script> from input
    # This prevents XSS attacks where someone injects HTML or JavaScript
    # into a text field hoping it gets executed in someone's browser
    clean = re.sub(r'<[^>]+>', '', v)
    return clean.strip()


def check_injection(v: str) -> str:
    # Blocks characters commonly used in NoSQL injection attacks against MongoDB
    # For example someone might type {"$gt": ""} in a field to bypass authentication
    for char in DANGEROUS_CHARACTERS:
        if char in v:
            raise ValueError(f"Input contains invalid character: {char}")
    return v


def validate_password_strength(v: str) -> str:
    # This is a reusable function so we do not repeat the same
    # password rules in RegisterSchema, ResetPasswordSchema and ChangePasswordSchema
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")

    # bcrypt has a 72 byte limit so we cap at 64 to be safe
    if len(v) > 64:
        raise ValueError("Password must not exceed 64 characters")

    # Each of these checks adds complexity making the password harder to crack
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
        raise ValueError("Password must contain at least one special character like !@#$%")

    # Spaces in passwords cause issues with some systems and are generally avoided
    if " " in v:
        raise ValueError("Password must not contain spaces")

    # Block the most commonly used passwords that hackers always try first
    if v.lower() in COMMON_PASSWORDS:
        raise ValueError("This password is too common. Please choose a stronger password")

    return v


# ─────────────────────────────────────────────
# REGISTER
# Validates the data when a new user signs up
# ─────────────────────────────────────────────
class RegisterSchema(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        v = strip_html_tags(v)
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 50:
            raise ValueError("Name must not exceed 50 characters")
        if not all(c.isalpha() or c.isspace() for c in v):
            raise ValueError("Name must contain only letters and spaces")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        # Strip whitespace and convert to lowercase for consistency
        v = v.strip().lower()
        if len(v) > 100:
            raise ValueError("Email must not exceed 100 characters")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        v = v.strip()
        # Allow + for international format like +94771234567
        if not v.replace("+", "").replace(" ", "").isdigit():
            raise ValueError("Phone number must contain only digits")
        clean_phone = v.replace("+", "").replace(" ", "")
        if len(clean_phone) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        # International phone numbers are max 15 digits (E.164 standard)
        if len(clean_phone) > 15:
            raise ValueError("Phone number must not exceed 15 digits")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        # Runs through the full password policy defined above
        return validate_password_strength(v)


# ─────────────────────────────────────────────
# LOGIN
# Validates the data when a user logs in
# We keep validation minimal here — we do not want to give
# hackers hints about what fields are wrong
# ─────────────────────────────────────────────
class LoginSchema(BaseModel):
    # Either email or phone must be provided — not both required
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v is not None:
            v = v.strip().lower()
            if len(v) > 100:
                raise ValueError("Email must not exceed 100 characters")
        return v

    @field_validator("phone")
    @classmethod
    def email_or_phone_required(cls, v, values):
        # Make sure at least one identifier was provided
        if not v and not values.data.get("email"):
            raise ValueError("Either email or phone number must be provided")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        # Only check max length here — we do not run full strength validation
        # because this is a login not a registration
        if len(v) > 64:
            raise ValueError("Invalid credentials")
        return v


# ─────────────────────────────────────────────
# VERIFY OTP
# Validates the data when a user submits their OTP
# ─────────────────────────────────────────────
class VerifyOTPSchema(BaseModel):
    email: EmailStr
    otp: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v):
        v = v.strip()
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v


# ─────────────────────────────────────────────
# FORGOT PASSWORD
# Validates the email when a user requests a password reset
# ─────────────────────────────────────────────
class ForgotPasswordSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = v.strip().lower()
        if len(v) > 100:
            raise ValueError("Email must not exceed 100 characters")
        return v


# ─────────────────────────────────────────────
# RESET PASSWORD
# Validates the data when a user resets their password using an OTP
# ─────────────────────────────────────────────
class ResetPasswordSchema(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v):
        v = v.strip()
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, values):
        if "new_password" in values.data and v != values.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# ─────────────────────────────────────────────
# CHANGE PASSWORD
# Validates the data when a logged in user changes their password
# ─────────────────────────────────────────────
class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, values):
        if "new_password" in values.data and v != values.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# ─────────────────────────────────────────────
# REFRESH TOKEN
# Validates the refresh token when a user wants a new access token
# ─────────────────────────────────────────────
class RefreshTokenSchema(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Invalid refresh token")
        if len(v) > 500:
            raise ValueError("Invalid refresh token")
        return v


# ─────────────────────────────────────────────
# UPDATE PROFILE
# Validates the data when a user updates their profile
# All fields are optional — they can update just one or all at once
# ─────────────────────────────────────────────
class UpdateProfileSchema(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    profile_picture: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            v = strip_html_tags(v)
            if len(v) < 2:
                raise ValueError("Name must be at least 2 characters long")
            if len(v) > 50:
                raise ValueError("Name must not exceed 50 characters")
            if not all(c.isalpha() or c.isspace() for c in v):
                raise ValueError("Name must contain only letters and spaces")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            v = v.strip()
            if not v.replace("+", "").replace(" ", "").isdigit():
                raise ValueError("Phone number must contain only digits")
            clean_phone = v.replace("+", "").replace(" ", "")
            if len(clean_phone) < 10:
                raise ValueError("Phone number must be at least 10 digits")
            if len(clean_phone) > 15:
                raise ValueError("Phone number must not exceed 15 digits")
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v):
        if v is not None:
            v = strip_html_tags(v)
            if len(v) < 5:
                raise ValueError("Address must be at least 5 characters long")
            if len(v) > 200:
                raise ValueError("Address must not exceed 200 characters")
            check_injection(v)
        return v

    @field_validator("profile_picture")
    @classmethod
    def validate_profile_picture(cls, v):
        if v is not None:
            v = v.strip()
            if not v.startswith(("http://", "https://")):
                raise ValueError("Profile picture must be a valid URL starting with http or https")
            if len(v) > 500:
                raise ValueError("Profile picture URL must not exceed 500 characters")
        return v


# ─────────────────────────────────────────────
# SECURITY SCHEMAS
# Biometric removed — only 2FA, login alerts and auto lock remain
# ─────────────────────────────────────────────

class Toggle2FASchema(BaseModel):
    # Password required to disable 2FA
    # Confirms it is the real user making the change
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Password is required")
        if len(v) > 64:
            raise ValueError("Invalid password")
        return v


class Verify2FASchema(BaseModel):
    # OTP submitted to confirm enabling or verifying 2FA
    otp: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v):
        v = v.strip()
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v


class ToggleLoginAlertsSchema(BaseModel):
    # True means send alert emails on login
    # False means do not send alert emails on login
    enabled: bool


class SetAutoLockSchema(BaseModel):
    # How many minutes of inactivity before the session auto locks
    # Flutter reads this value and starts an inactivity timer
    minutes: int

    @field_validator("minutes")
    @classmethod
    def validate_minutes(cls, v):
        # Only allow sensible values
        allowed = [1, 5, 10, 15, 30, 60]
        if v not in allowed:
            raise ValueError(f"Auto lock must be one of: {allowed} minutes")
        return v


# ─────────────────────────────────────────────
# TERMS AND CONDITIONS SCHEMA
# Only terms_of_service is required
# ─────────────────────────────────────────────
class TermsSchema(BaseModel):
    # Only one required checkbox
    terms_of_service: bool


# ─────────────────────────────────────────────
# DISTRICT SCHEMA
# Validates the district selection from Flutter
# ─────────────────────────────────────────────
class DistrictSchema(BaseModel):
    # The name of the selected district
    # Must be one of the 25 valid Sri Lanka districts
    # Full validation is done in district_routes.py
    # against the SRI_LANKA_DISTRICTS list
    district: str

    @field_validator("district")
    @classmethod
    def validate_district(cls, v):
        # Strip whitespace from both ends
        v = v.strip()

        # District name cannot be empty
        if len(v) == 0:
            raise ValueError("District cannot be empty")

        # District name cannot be too long — prevents extremely long inputs
        if len(v) > 50:
            raise ValueError("Invalid district name")

        return v