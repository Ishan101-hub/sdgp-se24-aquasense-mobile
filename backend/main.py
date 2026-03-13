# main.py
# AquaSense v3.1 – FastAPI application entry point

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
from leak_service import set_publish_queue as leak_set_publish_queue
from auth_router import router as auth_router
from analytics_router import router as analytics_router
from device_router import router as device_router
from device_router import set_publish_queue
from mobile_router import router as mobile_router          # ← NEW
from mobile_router import set_mobile_publish_queue         # ← NEW

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("aquasense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified ✓")

    publish_queue: asyncio.Queue = asyncio.Queue()
    set_publish_queue(publish_queue)
    leak_set_publish_queue(publish_queue)
    set_mobile_publish_queue(publish_queue)                # ← NEW

    tasks = [
        asyncio.create_task(start_mqtt_listener(publish_queue), name="mqtt"),
        asyncio.create_task(periodic_flush(),       name="batch_flush"),
        asyncio.create_task(schedule_aggregation(), name="aggregation"),
    ]
    logger.info("AquaSense v3.1 started — %d background tasks running ✓", len(tasks))

    yield

    for task in tasks:
        task.cancel()
    await engine.dispose()
    logger.info("AquaSense backend shut down cleanly.")


app = FastAPI(
    title="AquaSense API",
    description="IoT Smart Water Monitoring System — production backend",
    version="3.1.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
_env = os.getenv("ENVIRONMENT", "production").lower()

_production_origins: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "https://app.aquasense.com").split(",")
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
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)

app.include_router(auth_router)
app.include_router(device_router)
app.include_router(analytics_router)
app.include_router(mobile_router)                          # ← NEW


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "AquaSense", "version": "3.1.0"}


if __name__ == "__main__":
    import uvicorn
    config = uvicorn.Config("main:app", host="0.0.0.0", port=8000, reload=False)
    server = uvicorn.Server(config)
    asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)