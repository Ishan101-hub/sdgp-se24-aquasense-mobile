# main.py
# AquaSense — Unified FastAPI application entry point

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
from mqtt_service import start_mqtt_listener, periodic_flush, set_leak_service as mqtt_set_leak_service
from aggregation import schedule_aggregation
from leak_service import LeakDetectionService, set_leak_service, EventType
from installation_router import router as installation_router

# ── Auth routers (Kulith) ─────────────────────────────────────
from app.routes.auth_routes        import router as auth_router
from app.routes.user_routes        import router as user_router
from app.routes.google_auth_routes import router as google_auth_router
from app.routes.security_routes    import router as security_router
from app.routes.terms_routes       import router as terms_router
from app.routes.district_routes    import router as district_router

# ── IoT routers (main backend) ────────────────────────────────
from analytics_router import router as analytics_router
from device_router    import router as device_router, set_publish_queue
from mobile_router    import router as mobile_router, set_mobile_publish_queue
from usage_router     import router as usage_router
from reports_router import router as reports_router

from firebase_service import init_firebase, send_leak_push

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("aquasense")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified ✓")

    init_firebase()

    # Shared publish queue — all valve command sources write here
    publish_queue: asyncio.Queue = asyncio.Queue()
    set_publish_queue(publish_queue)
    set_mobile_publish_queue(publish_queue)

    # ── Leak detection callbacks ──────────────────────────────────────────────

    async def _on_event_created(
        zone_id: int, event_type: EventType, message: str, details: dict
    ) -> None:
        """Write a leak/cleared event to the events table."""
        from database import AsyncSessionLocal
        from models import Device, Event
        from sqlalchemy import select
        try:
            async with AsyncSessionLocal() as db:
                dev_result = await db.execute(
                    select(Device).where(
                        Device.zone_id     == zone_id,
                        Device.sensor_type == "inlet",
                        Device.status      == "active",
                    ).limit(1)
                )
                device = dev_result.scalar_one_or_none()
                if not device:
                    logger.warning("on_event_created: no inlet device for zone_id=%d", zone_id)
                    return
                db.add(Event(
                    device_id   = device.device_id,
                    network_id  = device.network_id,
                    zone_id     = zone_id,
                    event_type  = event_type.value,
                    description = message,
                ))
                await db.commit()
                logger.info("Event saved: zone=%d type=%s", zone_id, event_type.value)
        except Exception as exc:
            logger.error("Failed to save event zone=%d: %s", zone_id, exc)

    async def _on_valve_command(zone_id: int, action: str) -> None:
        """Send valve command to the inlet ESP32 — backup action after leak confirmed."""
        from database import AsyncSessionLocal
        from models import Device, Zone, Network, ValveLog
        from sqlalchemy import select, update
        try:
            async with AsyncSessionLocal() as db:
                zone_result = await db.execute(
                    select(Zone.zone_name, Network.network_id)
                    .join(Network, Zone.network_id == Network.id)
                    .where(Zone.id == zone_id)
                )
                zone_net = zone_result.one_or_none()
                if not zone_net:
                    logger.warning("_on_valve_command: zone_id=%d not found", zone_id)
                    return
                # Handle zone key logic
                zone_slug, network_slug = zone_id, zone_net.network_id

                dev_result = await db.execute(
                    select(Device).where(
                        Device.zone_id     == zone_id,
                        Device.sensor_type == "inlet",
                        Device.status      == "active",
                    )
                )
                devices = dev_result.scalars().all()
                for device in devices:
                    await db.execute(
                        update(Device)
                        .where(Device.device_id == device.device_id)
                        .values(valve_state=action)
                    )
                    db.add(ValveLog(
                        device_id    = device.device_id,
                        commanded_by = None,
                        action       = action,
                        source       = "auto_leak",
                    ))
                    await publish_queue.put((network_slug, zone_slug, device.device_id, action))
                    logger.warning(
                        "BACKUP VALVE CMD zone=%d device=%s action=%s",
                        zone_id, device.device_id, action,
                    )
                await db.commit()
        except Exception as exc:
            logger.error("Failed to send valve command zone=%d: %s", zone_id, exc)

    async def _on_leak_detected(zone_id: str, inlet_flow: float, outlet_flow: float) -> None:
        """Fixed Alignment: Properly triggers the live push architecture."""
        logger.warning(
            "LEAK ALERT zone=%s inlet=%.2f outlet=%.2f",
            zone_id, inlet_flow, outlet_flow,
        )

        from database import AsyncSessionLocal
        from models import Zone, Network, User
        from sqlalchemy import select

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Zone.zone_name, User.fcm_token)
                    .join(Network, Zone.network_id == Network.id)
                    .join(User, Network.owner_id == User.id)
                    .where(Zone.id == zone_id) 
                )
                
                row = result.one_or_none()
                if row:
                    zone_name, fcm_token = row 
                    if fcm_token:
                        await send_leak_push(fcm_token, zone_name, zone_id)
                    else:
                        logger.warning("No FCM token found for zone=%s owner", zone_id)
                else:
                    logger.warning("Zone %s not found in database", zone_id)
        except Exception as exc:
            logger.error("Exception during leak notification dispatch for zone %s: %s", zone_id, exc)

    # ── Instantiate and register the leak detection service ──────────────────
    leak_svc = LeakDetectionService(
        on_leak_detected = _on_leak_detected,
        on_valve_command = _on_valve_command,
        on_event_created = _on_event_created,
    )
    set_leak_service(leak_svc)
    mqtt_set_leak_service(leak_svc)

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
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "https://aquasense-sdgp.web.app").split(",")
    if o.strip()
]
_dev_origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://192.168.1.3:8000",
    "http://192.168.8.183",
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
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(google_auth_router)
app.include_router(security_router)
app.include_router(terms_router)
app.include_router(district_router)

app.include_router(device_router)
app.include_router(analytics_router)
app.include_router(mobile_router)
app.include_router(usage_router)
app.include_router(reports_router)
app.include_router(installation_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "AquaSense", "version": "3.1.0"}

@app.get("/", tags=["system"])
async def root():
    return {"message": "AquaSense API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)