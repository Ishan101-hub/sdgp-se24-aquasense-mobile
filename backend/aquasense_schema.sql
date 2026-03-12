# ─── AquaSense environment configuration ──────────────────────────────────────
# Copy this file to .env and fill in real values.
# NEVER commit .env to version control.

# ── Runtime environment ────────────────────────────────────────────────────────
# "production" (default) → only CORS_ALLOWED_ORIGINS are permitted
# "development"          → also allows http://localhost:3000 and :8080
ENVIRONMENT=production

# ── CORS ──────────────────────────────────────────────────────────────────────
# Comma-separated list of allowed frontend origins. No trailing slashes.
# Production example:
CORS_ALLOWED_ORIGINS=https://app.aquasense.com
# Multiple origins:
# CORS_ALLOWED_ORIGINS=https://app.aquasense.com,https://admin.aquasense.com

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aquasense

# ── JWT ────────────────────────────────────────────────────────────────────────
JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ── MQTT (HiveMQ) ──────────────────────────────────────────────────────────────
MQTT_HOST=your-hivemq-host
MQTT_PORT=8883
MQTT_USERNAME=your-mqtt-user
MQTT_PASSWORD=your-mqtt-password
