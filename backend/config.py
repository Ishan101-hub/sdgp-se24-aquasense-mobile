# config.py
# AquaSense v3 — Application settings
# All values are loaded from .env automatically by pydantic-settings.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET:                   str
    JWT_ALGORITHM:                str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:  int = 30

    # ── MQTT ──────────────────────────────────────────────────
    # Topic subscriptions and valve publish format are hardcoded
    # in mqtt_service.py using the v3 hierarchical wildcard pattern.
    # MQTT_TOPIC_READINGS and MQTT_TOPIC_VALVE from v2 are removed.
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