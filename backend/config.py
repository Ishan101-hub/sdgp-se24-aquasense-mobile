# config.py
# AquaSense v3.1 — Application settings
# Merges AquaSense IoT settings with Kulith's auth settings.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Database (Supabase PostgreSQL) ────────────────────────
    DATABASE_URL: str

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET:                  str
    JWT_ALGORITHM:               str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Email — Gmail SMTP (Kulith's OTP emails) ──────────────
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASS: str = ""

    # ── Google OAuth (Kulith's Google login) ──────────────────
    GOOGLE_CLIENT_ID:     str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI:  str = ""

    # ── Fernet encryption (Kulith — phone/address at rest) ────
    ENCRYPTION_KEY: str = ""

    # ── MQTT (HiveMQ Cloud) ───────────────────────────────────
    MQTT_BROKER_HOST: str
    MQTT_BROKER_PORT: int = 8883
    MQTT_USERNAME:    str
    MQTT_PASSWORD:    str
    MQTT_CLIENT_ID:   str = "aquasense-backend"

    # ── Batch write tuning ────────────────────────────────────
    INSERT_BATCH_SIZE:          int = 50
    INSERT_BATCH_FLUSH_SECONDS: int = 5

    # ── Leak detection ────────────────────────────────────────
    LEAK_FLOW_THRESHOLD_LPM:  float = 25.0
    LEAK_SEVERITY_MEDIUM:     float = 25.0
    LEAK_SEVERITY_HIGH:       float = 40.0
    AUTO_CLOSE_VALVE_ON_HIGH: bool  = True

    # ── CORS ──────────────────────────────────────────────────
    ENVIRONMENT:          str = "production"
    CORS_ALLOWED_ORIGINS: str = "https://app.aquasense.com"

    class Config:
        env_file = ".env"


settings = Settings()