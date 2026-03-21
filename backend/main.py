# main.py
# AquaSense — Unified FastAPI application entry point
#
# Registers all routers from both backends:
#
# Auth system (Kulith):
#   /auth/*       — register, login, OTP, 2FA, refresh, logout, password
#   /user/*       — profile, update, device registration, delete
#   /auth/google  — Google OAuth
#   /security/*   — 2FA toggle, login alerts, auto-lock
#   /terms/*      — terms acceptance
#   /district/*   — Sri Lanka district selection
#
# IoT system (main backend):
#   /networks/*   — network management
#   /zones/*      — zone management
#   /devices/*    — device management and valve control
#   /analytics/*  — live data, daily/monthly usage, zone summaries
#   /mobile/*     — Flutter-shaped convenience endpoints
#
# Background tasks:
#   MQTT listener, batch flush, nightly aggregation

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import engine
from models import Base
from mqtt_service import start_mqtt_listener, periodic_flush
from aggregation import schedule_aggregation
from leak_service import set_publish_queue as leak_set_publish_queue

# ── Auth routers (Kulith) ─────────────────────────────────────
from app.routes.auth_routes     import router as auth_router
from app.routes.user_routes     import router as user_router
from app.routes.google_auth_routes import router as google_auth_router
from app.routes.security_routes import router as security_router
from app.routes.terms_routes    import router as terms_router
from app.routes.district_routes import router as district_router

# ── IoT routers (main backend) ────────────────────────────────
from analytics_router import router as analytics_router
from device_router    import router as device_router, set_publish_queue
from mobile_router    import router as mobile_router, set_mobile_publish_queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("aquasense")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on startup from SQLAlchemy models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified ✓")

    # Single publish queue shared across all valve command sources
    publish_queue: asyncio.Queue = asyncio.Queue()
    set_publish_queue(publish_queue)
    leak_set_publish_queue(publish_queue)
    set_mobile_publish_queue(publish_queue)

    tasks = [
        asyncio.create_task(start_mqtt_listener(publish_queue), name="mqtt"),
        asyncio.create_task(periodic_flush(),       name="batch_flush"),
        asyncio.create_task(schedule_aggregation(), name="aggregation"),
    ]
    logger.info("AquaSense started — %d background tasks running ✓", len(tasks))

    yield

    for task in tasks:
        task.cancel()
    await engine.dispose()
    logger.info("AquaSense shut down cleanly.")


app = FastAPI(
    title="AquaSense API",
    description="IoT Smart Water Monitoring System",
    version="3.1.0",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────
_env = os.getenv("ENVIRONMENT", "production").lower()

_production_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "https://app.aquasense.com").split(",")
    if o.strip()
]
_dev_origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://127.0.0.1:3000",
]
_allowed_origins = (
    _production_origins + _dev_origins if _env == "development" else _production_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)

# ── Global exception handler ──────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )

# ── Routers ───────────────────────────────────────────────────
# Auth system (Kulith)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(google_auth_router)
app.include_router(security_router)
app.include_router(terms_router)
app.include_router(district_router)

# IoT system
app.include_router(device_router)
app.include_router(analytics_router)
app.include_router(mobile_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "AquaSense", "version": "3.1.0"}

@app.get("/", tags=["system"])
async def root():
    return {"message": "AquaSense API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
