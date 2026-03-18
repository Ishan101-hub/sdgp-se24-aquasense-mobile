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