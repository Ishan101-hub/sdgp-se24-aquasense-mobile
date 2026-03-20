import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# SUPABASE SETTINGS
# Replaces MongoDB connection
# ─────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ─────────────────────────────────────────────
# JWT SETTINGS
# ─────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ─────────────────────────────────────────────
# EMAIL SETTINGS
# ─────────────────────────────────────────────
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# ─────────────────────────────────────────────
# GOOGLE OAUTH SETTINGS
# ─────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# ─────────────────────────────────────────────
# ENCRYPTION SETTINGS
# ─────────────────────────────────────────────
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")