import os
from dotenv import load_dotenv

# Load all the variables from the .env file into the environment
# This must run before any os.getenv() calls
load_dotenv()

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

# The full MongoDB Atlas connection string
MONGO_URL = os.getenv("MONGO_URL")

# The name of the database inside MongoDB
DB_NAME = os.getenv("DB_NAME")


# ─────────────────────────────────────────────
# JWT SETTINGS
# ─────────────────────────────────────────────

# A long random secret string used to sign and verify JWT tokens
# If this leaks, anyone can forge tokens — keep it safe
SECRET_KEY = os.getenv("SECRET_KEY")

# The algorithm used to sign JWT tokens — HS256 is the most common
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# How long the access token stays valid — defaults to 30 minutes
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# ─────────────────────────────────────────────
# EMAIL SETTINGS
# ─────────────────────────────────────────────

# Gmail SMTP server address
EMAIL_HOST = os.getenv("EMAIL_HOST")

# Port 587 is the standard port for sending emails with TLS
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))

# The Gmail address that sends the OTP emails
EMAIL_USER = os.getenv("EMAIL_USER")

# The Gmail App Password — not your regular Gmail password
# Generate this from Google Account → Security → App Passwords
EMAIL_PASS = os.getenv("EMAIL_PASS")


# ─────────────────────────────────────────────
# GOOGLE OAUTH SETTINGS
# ─────────────────────────────────────────────

# Google OAuth client ID from Google Cloud Console
# Found under APIs and Services → Credentials → AquaSense Web Client
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Google OAuth client secret from Google Cloud Console
# Keep this safe — anyone with this can impersonate your app
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# The URL Google redirects to after the user approves login
# Must match exactly what is set in Google Cloud Console
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


# ─────────────────────────────────────────────
# ENCRYPTION SETTINGS
# ─────────────────────────────────────────────

# A Fernet encryption key used to encrypt and decrypt sensitive user data
# such as phone numbers and addresses before storing them in MongoDB
# Generate this key by running:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# If this key is lost all encrypted data becomes unreadable — keep it safe
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")