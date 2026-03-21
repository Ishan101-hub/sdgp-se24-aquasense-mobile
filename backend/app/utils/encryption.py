# app/utils/encryption.py
# AquaSense — Fernet encryption for sensitive user fields
# Kulith's encryption.py adapted to read from config.settings.

from cryptography.fernet import Fernet
from config import settings


def _fernet() -> Fernet:
    """Creates a fresh Fernet instance from the configured key."""
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    """
    Encrypts a plain text string.
    Returns None if value is None.
    Example: "+94771234567" → "gAAAAABl..."
    """
    if value is None:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """
    Decrypts an encrypted string back to plain text.
    Returns None if value is None.
    Example: "gAAAAABl..." → "+94771234567"
    """
    if value is None:
        return None
    return _fernet().decrypt(value.encode()).decode()
