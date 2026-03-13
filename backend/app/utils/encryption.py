from cryptography.fernet import Fernet
from app.config import ENCRYPTION_KEY

# Fernet is a symmetric encryption method
# The same key is used to encrypt and decrypt
# If the key is lost the data cannot be recovered — keep it safe
fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    # Converts plain text into encrypted bytes then stores as a string
    # Example: "+94771234567" → "gAAAAABl..."
    if value is None:
        return None
    return fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    # Converts encrypted string back to plain text
    # Example: "gAAAAABl..." → "+94771234567"
    if value is None:
        return None
    return fernet.decrypt(value.encode()).decode()