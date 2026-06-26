# config.py
# AquaSense — Unified application settings
# Merges both backends into a single pydantic-settings class.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET:                  str
    JWT_ALGORITHM:               str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Email — Gmail SMTP ────────────────────────────────────
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASS: str = ""

    # ── Resend E-mail API Key ─────────────────────────────────
    RESEND_API_KEY: str

    # ── Google OAuth ──────────────────────────────────────────
    GOOGLE_CLIENT_ID:     str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI:  str = ""

    # ── Fernet encryption ─────────────────────────────────────
    ENCRYPTION_KEY: str = ""

    # ── MQTT ──────────────────────────────────────────────────
    MQTT_BROKER_HOST: str
    MQTT_BROKER_PORT: int   = 8883
    MQTT_USERNAME:    str
    MQTT_PASSWORD:    str
    MQTT_CLIENT_ID:   str   = "aquasense-backend"

    # ── Batch write tuning ────────────────────────────────────
    INSERT_BATCH_SIZE:          int = 50
    INSERT_BATCH_FLUSH_SECONDS: int = 5

    # ── Leak detection — ESP32-matched values ─────────────────
    # These MUST stay in sync with ESP32 firmware constants.
    FLOW_MISMATCH_THRESHOLD_LPM: float = 0.8   # L/min delta to consider a mismatch
    LEAK_CONFIRM_COUNT:          int   = 3     # consecutive readings before confirming
    HEARTBEAT_TIMEOUT_SEC:       float = 5.0   # seconds before outlet considered offline

    # ── Leak detection — auto-close thresholds ────────────────
    LEAK_FLOW_THRESHOLD_LPM:  float = 25.0
    LEAK_SEVERITY_HIGH:       float = 40.0
    AUTO_CLOSE_VALVE_ON_HIGH: bool  = True

    # ── Extended alert thresholds ─────────────────────────────
    HIGH_FLOW_THRESHOLD_LPM:        float = 15.0  # tap left open alert
    HIGH_FLOW_DURATION_SEC:         int   = 300   # seconds before alerting
    BURST_FLOW_THRESHOLD_LPM:       float = 50.0  # burst pipe detection
    VALVE_STUCK_FLOW_THRESHOLD_LPM: float = 0.5   # flow after valve close
    VALVE_STUCK_CHECK_DELAY_SEC:    int   = 3     # seconds after close before checking

    # ── Water bill estimation ─────────────────────────────────
    WATER_BILL_RATE_PER_1000L: float = 55.0   # LKR

    # ── CORS ──────────────────────────────────────────────────
    ENVIRONMENT:          str = "production"
    CORS_ALLOWED_ORIGINS: str = "https://aquasense-sdgp.web.app"

    # base64 output
    FIREBASE_CREDENTIALS_JSON: str = ""

    # Unified configuration layer
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid"
    )


settings = Settings()

# Convenience aliases — Kulith's files import these directly
SECRET_KEY                  = settings.JWT_SECRET
ALGORITHM                   = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# ESP32-matched leak detection constants — imported directly by leak_service.py
FLOW_MISMATCH_THRESHOLD_LPM = settings.FLOW_MISMATCH_THRESHOLD_LPM
LEAK_CONFIRM_COUNT       = settings.LEAK_CONFIRM_COUNT
HEARTBEAT_TIMEOUT_SEC    = settings.HEARTBEAT_TIMEOUT_SEC