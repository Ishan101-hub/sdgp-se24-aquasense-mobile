# main.py
# AquaSense v2 – FastAPI application entry point

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models import Base
from mqtt_service import start_mqtt_listener, periodic_flush
from aggregation import schedule_aggregation
from auth_router import router as auth_router
from analytics_router import router as analytics_router
from device_router import router as device_router
from device_router import set_publish_queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("aquasense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (use Alembic for production migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified ✓")

    # Shared MQTT publish queue
    publish_queue: asyncio.Queue = asyncio.Queue()
    set_publish_queue(publish_queue)

    # Background tasks
    tasks = [
        asyncio.create_task(start_mqtt_listener(publish_queue), name="mqtt"),
        asyncio.create_task(periodic_flush(), name="batch_flush"),
        asyncio.create_task(schedule_aggregation(), name="aggregation"),
    ]
    logger.info("AquaSense backend started — %d background tasks running ✓", len(tasks))

    yield   # Application is running

    for task in tasks:
        task.cancel()
    await engine.dispose()
    logger.info("AquaSense backend shut down cleanly.")


app = FastAPI(
    title="AquaSense API",
    description="IoT Smart Water Monitoring System — production backend",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS – environment-aware, no wildcards in production
#
# Set in environment / .env:
#   ENVIRONMENT=production          (default)
#   CORS_ALLOWED_ORIGINS=https://app.aquasense.com,https://admin.aquasense.com
#
# In development add http://localhost:3000 to CORS_ALLOWED_ORIGINS, or set
#   ENVIRONMENT=development  (automatically appends localhost origins below)
# ---------------------------------------------------------------------------
_env = os.getenv("ENVIRONMENT", "production").lower()

_production_origins: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.aquasense.com",
    ).split(",")
    if origin.strip()
]

_dev_origins: list[str] = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
]

_allowed_origins: list[str] = (
    _production_origins + _dev_origins if _env == "development" else _production_origins
)

app.add_middleware(
    CORSMiddleware,
    # Explicit list – never "*" when allow_credentials=True
    allow_origins=_allowed_origins,
    # Required for Authorization header + cookies (refresh-token flow)
    allow_credentials=True,
    # Only the HTTP verbs your API actually exposes
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    # Authorization carries the JWT Bearer token; Content-Type is needed for
    # JSON/form request bodies; Accept allows the client to negotiate format
    allow_headers=["Authorization", "Content-Type", "Accept"],
    # Cache preflight response for 10 minutes to reduce OPTIONS round-trips
    max_age=600,
)

app.include_router(auth_router)
app.include_router(device_router)
app.include_router(analytics_router)

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "AquaSense", "version": "2.0.0"}
