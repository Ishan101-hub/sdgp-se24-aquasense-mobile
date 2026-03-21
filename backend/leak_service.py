# leak_service.py
# AquaSense v3 — Leak detection
#
# Changes from v2:
#   • evaluate_reading() receives network_id, zone_id for Event creation
#   • Event gains zone_id FK
#   • publish_queue item is now a 4-tuple (network_id, zone_id, device_id, action)
#
# New in v3.1:
#   • evaluate_flow_mismatch() — backend inlet/outlet delta check
#     Creates a "flow_mismatch" event when inlet_flow - outlet_flow >= threshold.
#     Called from mqtt_service after pairing the latest inlet+outlet readings
#     for a zone when either sensor publishes a new reading.

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from database import AsyncSessionLocal
from models import Device, Event, ValveLog, Zone, Network
from config import settings
logger = logging.getLogger("aquasense.leak")

# Dedup: key = device_id → last event timestamp
_last_leak_event: dict[str, datetime] = {}

# Dedup for flow_mismatch: key = zone_id (integer PK) → last event timestamp
_last_mismatch_event: dict[int, datetime] = {}

DEDUP_WINDOW_SECONDS = 60

# Flow mismatch threshold: inlet - outlet delta that indicates a leak
FLOW_MISMATCH_THRESHOLD_LPM: float = 2.0   # configurable; lower than LEAK_FLOW_THRESHOLD

# publish_queue is injected from main.py via set_publish_queue()
_publish_queue = None


def set_publish_queue(q) -> None:
    global _publish_queue
    _publish_queue = q


def classify_severity(flow_rate: float) -> str:
    if flow_rate >= settings.LEAK_SEVERITY_HIGH:
        return "high"
    elif flow_rate >= settings.LEAK_SEVERITY_MEDIUM:
        return "medium"
    return "low"


def classify_mismatch_severity(delta: float) -> str:
    """Severity based on inlet-outlet delta."""
    if delta >= settings.LEAK_SEVERITY_HIGH:
        return "high"
    elif delta >= settings.LEAK_SEVERITY_MEDIUM:
        return "medium"
    return "low"


async def evaluate_reading(
    device_id:    str,
    network_id:   str,    # MQTT string slug
    zone_id:      str,    # MQTT string slug
    flow_rate:    float,
    total_volume: float,
    timestamp:    datetime,
) -> None:
    """
    Evaluate a single outlet reading for absolute flow leak conditions.
    Triggers when flow_rate exceeds LEAK_FLOW_THRESHOLD_LPM.
    Creates a 'leak_detected' Event and optionally publishes a valve close command.
    """
    if flow_rate <= settings.LEAK_FLOW_THRESHOLD_LPM:
        return   # Normal reading

    # Dedup check
    last = _last_leak_event.get(device_id)
    if last and (timestamp - last).total_seconds() < DEDUP_WINDOW_SECONDS:
        return

    severity = classify_severity(flow_rate)
    _last_leak_event[device_id] = timestamp

    async with AsyncSessionLocal() as db:
        # Load device with zone/network for FK columns
        result = await db.execute(
            select(Device)
            .join(Zone,    Device.zone_id    == Zone.id)
            .join(Network, Device.network_id == Network.id)
            .where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            return

        event = Event(
            device_id   = device_id,
            network_id  = device.network_id,   # integer FK
            zone_id     = device.zone_id,       # integer FK
            event_type  = "leak_detected",
            severity    = severity,
            description = (
                f"Abnormal flow: {flow_rate:.2f} L/min "
                f"(threshold: {settings.LEAK_FLOW_THRESHOLD_LPM} L/min). "
                f"Severity: {severity}."
            ),
        )
        db.add(event)
        logger.warning(
            "LEAK | device=%s | network=%s | zone=%s | flow=%.2f | severity=%s",
            device_id, network_id, zone_id, flow_rate, severity,
        )

        # Auto-close on high severity
        if (
            severity == "high"
            and settings.AUTO_CLOSE_VALVE_ON_HIGH
            and device.valve_state == "open"
        ):
            await db.execute(
                update(Device)
                .where(Device.device_id == device_id)
                .values(valve_state="closed")
            )
            db.add(ValveLog(
                device_id    = device_id,
                commanded_by = None,
                action       = "close",
                source       = "auto_leak",
            ))
            logger.warning("AUTO-CLOSE valve for device=%s", device_id)

            if _publish_queue:
                # 4-tuple: (network_id_slug, zone_id_slug, device_id, action)
                await _publish_queue.put((network_id, zone_id, device_id, "close"))

        await db.commit()


async def evaluate_flow_mismatch(
    zone_pk:          int,    # Zone.id (integer PK)
    network_id:       str,    # MQTT string slug (for logging / valve publish)
    zone_id:          str,    # MQTT string slug (for logging / valve publish)
    inlet_flow:       float,
    outlet_flow:      float,
    outlet_device_id: str,
    timestamp:        datetime,
) -> None:
    """
    Compare inlet vs outlet flow rates for a zone and create a 'flow_mismatch'
    event when the delta exceeds FLOW_MISMATCH_THRESHOLD_LPM.

    Called from mqtt_service._process_outlet_reading() after fetching the most
    recent inlet reading for the same zone.

    Only fires when the outlet valve is open (if it's closed, delta is expected).
    Deduplicates per zone within DEDUP_WINDOW_SECONDS.
    """
    delta = inlet_flow - outlet_flow
    if delta < FLOW_MISMATCH_THRESHOLD_LPM:
        return   # Delta within acceptable range

    # Dedup check (zone-level, not device-level)
    last = _last_mismatch_event.get(zone_pk)
    if last and (timestamp - last).total_seconds() < DEDUP_WINDOW_SECONDS:
        return

    severity = classify_mismatch_severity(delta)
    _last_mismatch_event[zone_pk] = timestamp

    async with AsyncSessionLocal() as db:
        # Load the outlet device to get FK IDs and valve state
        result = await db.execute(
            select(Device).where(Device.device_id == outlet_device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            return

        # Only flag mismatch when outlet valve is open — if closed, delta is normal
        if device.valve_state != "open":
            return

        event = Event(
            device_id   = outlet_device_id,
            network_id  = device.network_id,
            zone_id     = device.zone_id,
            event_type  = "flow_mismatch",
            severity    = severity,
            description = (
                f"Inlet {inlet_flow:.2f} L/min vs outlet {outlet_flow:.2f} L/min "
                f"— delta {delta:.2f} L/min exceeds threshold "
                f"{FLOW_MISMATCH_THRESHOLD_LPM} L/min. Severity: {severity}."
            ),
        )
        db.add(event)
        logger.warning(
            "FLOW MISMATCH | zone_pk=%d | zone=%s | inlet=%.2f | outlet=%.2f | delta=%.2f | severity=%s",
            zone_pk, zone_id, inlet_flow, outlet_flow, delta, severity,
        )

        # Auto-close the outlet valve on high-severity mismatch
        if (
            severity == "high"
            and settings.AUTO_CLOSE_VALVE_ON_HIGH
        ):
            await db.execute(
                update(Device)
                .where(Device.device_id == outlet_device_id)
                .values(valve_state="closed")
            )
            db.add(ValveLog(
                device_id    = outlet_device_id,
                commanded_by = None,
                action       = "close",
                source       = "auto_leak",
            ))
            logger.warning("AUTO-CLOSE valve for device=%s (flow mismatch)", outlet_device_id)

            if _publish_queue:
                await _publish_queue.put((network_id, zone_id, outlet_device_id, "close"))

        await db.commit()