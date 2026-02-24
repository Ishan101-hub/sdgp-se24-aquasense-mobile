# app/leak_service.py
# AquaSense v2 – Leak detection and event generation

import logging
from datetime import datetime

from sqlalchemy import select
from database import AsyncSessionLocal
from models import Device, Event, ValveLog
from config import settings

logger = logging.getLogger("aquasense.leak")

# In-memory dedup: avoid creating duplicate events for sustained leaks
# Key = device_id → timestamp of last event created
_last_leak_event: dict[str, datetime] = {}
DEDUP_WINDOW_SECONDS = 60   # only one event per device per 60s


def classify_severity(flow_rate: float) -> str:
    if flow_rate >= settings.LEAK_SEVERITY_HIGH:
        return "high"
    elif flow_rate >= settings.LEAK_SEVERITY_MEDIUM:
        return "medium"
    return "low"


async def evaluate_reading(
    device_id: str,
    flow_rate: float,
    total_volume: float,
    timestamp: datetime,
) -> None:
    """
    Evaluate a single reading for leak conditions.
    Creates an event and optionally closes the valve.
    """
    if flow_rate <= settings.LEAK_FLOW_THRESHOLD_LPM:
        return  # Normal reading — nothing to do

    # Dedup: skip if we already raised an event recently
    last = _last_leak_event.get(device_id)
    if last and (timestamp - last).total_seconds() < DEDUP_WINDOW_SECONDS:
        return

    severity = classify_severity(flow_rate)
    _last_leak_event[device_id] = timestamp

    async with AsyncSessionLocal() as db:
        # Verify device exists
        result = await db.execute(select(Device).where(Device.device_id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            return

        # Create event
        event = Event(
            device_id=device_id,
            network_id=device.network_id,
            event_type="leak_detected",
            severity=severity,
            description=(
                f"Abnormal flow detected: {flow_rate:.2f} L/min "
                f"(threshold: {settings.LEAK_FLOW_THRESHOLD_LPM} L/min). "
                f"Severity: {severity}."
            ),
        )
        db.add(event)
        logger.warning(
            "LEAK | device=%s | flow=%.2f L/min | severity=%s",
            device_id, flow_rate, severity
        )

        # Auto-close valve on high severity
        if severity == "high" and settings.AUTO_CLOSE_VALVE_ON_HIGH and device.valve_state == "open":
            device.valve_state = "closed"
            valve_log = ValveLog(
                device_id=device_id,
                commanded_by=None,
                action="close",
                source="auto_leak",
            )
            db.add(valve_log)
            logger.warning("AUTO-CLOSE valve for device=%s", device_id)
            # Valve publish is handled by returning action to MQTT publish_queue
            # This is done by injecting publish_queue via set_publish_queue() in main.py

        await db.commit()
