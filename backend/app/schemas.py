# schemas.py
# AquaSense — Request validation schemas
# Kulith's schemas.py copied into the server root so auth_router.py can import them.
# All validation logic is unchanged from Kulith's original.

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re

COMMON_PASSWORDS = [
    "password", "password123", "123456", "12345678",
    "qwerty", "abc123", "letmein", "welcome",
    "monkey", "dragon", "master", "sunshine"
]

DANGEROUS_CHARACTERS = ["$", "{", "}", "<", ">", "\\", "|"]


def strip_html_tags(v: str) -> str:
    clean = re.sub(r'<[^>]+>', '', v)
    return clean.strip()


def check_injection(v: str) -> str:
    for char in DANGEROUS_CHARACTERS:
        if char in v:
            raise ValueError(f"Input contains invalid character: {char}")
    return v


def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(v) > 64:
        raise ValueError("Password must not exceed 64 characters")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
        raise ValueError("Password must contain at least one special character like !@#$%")
    if " " in v:
        raise ValueError("Password must not contain spaces")
    if v.lower() in COMMON_PASSWORDS:
        raise ValueError("This password is too common. Please choose a stronger password")
    return v


# ── REGISTER ──────────────────────────────────────────────────

class RegisterSchema(BaseModel):
    name:     str
    email:    EmailStr
    phone:    str
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = strip_html_tags(v.strip())
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
        v = v.strip().lower()
        if len(v) > 100:
            raise ValueError("Email must not exceed 100 characters")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        v = v.strip()
        if not v.replace("+", "").replace(" ", "").isdigit():
            raise ValueError("Phone number must contain only digits")
        clean = v.replace("+", "").replace(" ", "")
        if len(clean) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        if len(clean) > 15:
            raise ValueError("Phone number must not exceed 15 digits")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)


# ── LOGIN ─────────────────────────────────────────────────────

class LoginSchema(BaseModel):
    email:    Optional[EmailStr] = None
    phone:    Optional[str]      = None
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
        if not v and not values.data.get("email"):
            raise ValueError("Either email or phone number must be provided")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) > 64:
            raise ValueError("Invalid credentials")
        return v


# ── VERIFY OTP ────────────────────────────────────────────────

class VerifyOTPSchema(BaseModel):
    email: EmailStr
    otp:   str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v):
        v = v.strip()
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v


# ── FORGOT PASSWORD ───────────────────────────────────────────

class ForgotPasswordSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = v.strip().lower()
        if len(v) > 100:
            raise ValueError("Email must not exceed 100 characters")
        return v


# ── RESET PASSWORD ────────────────────────────────────────────

class ResetPasswordSchema(BaseModel):
    email:            EmailStr
    otp:              str
    new_password:     str
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


# ── CHANGE PASSWORD ───────────────────────────────────────────

class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password:     str
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


# ── REFRESH TOKEN ─────────────────────────────────────────────

class RefreshTokenSchema(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Invalid refresh token")
        if len(v) > 2000:
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