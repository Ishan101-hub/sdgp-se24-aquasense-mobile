# mqtt_service.py
# AquaSense v3 — Async MQTT service
#
# Topic structure (finalized):
#   aquasense/{network_id}/{zone_id}/{device_id}/{component}
#
# Subscriptions:
#   aquasense/+/+/+/outlet   — outlet sensor readings
#   aquasense/+/+/+/events   — leak and valve events from devices
#
# Valve publish:
#   aquasense/{network_id}/{zone_id}/{device_id}/valve
#
# Changes from v2:
#   • _parse_topic() extracts network_id, zone_id, device_id, component
#   • _validate_device() checks device exists AND belongs to the correct zone/network
#   • Reading rows now include network_id, zone_id, sensor_type (denormalised)
#   • publish_valve_command() uses full hierarchical topic
#   • outbound_loop() receives (network_id, zone_id, device_id, action) tuples
#   • Device.last_seen updated on every processed reading

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import aiomqtt
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import settings
from database import AsyncSessionLocal
from models import Device, Network, Zone, Reading, Event, ValveLog
from leak_service import evaluate_reading, evaluate_flow_mismatch

logger = logging.getLogger("aquasense.mqtt")

# ─── Batch write buffer ───────────────────────────────────────────────────────
# Readings are accumulated here and flushed to PostgreSQL in bulk every N seconds
# or when the buffer hits INSERT_BATCH_SIZE rows — whichever comes first.
_reading_buffer: list[dict] = []
_buffer_lock = asyncio.Lock()

# ─── In-process device cache ──────────────────────────────────────────────────
# Caches (network_id_str, zone_id_str) → Device ORM row to avoid a DB round-trip
# on every single MQTT message. Invalidated when a new device is registered.
_device_cache: dict[str, Optional[Device]] = {}


def invalidate_device_cache(device_id: str) -> None:
    """Called by device_router after registering or updating a device."""
    _device_cache.pop(device_id, None)


# ─────────────────────────────────────────────────────────────────────────────
#  Topic parsing
# ─────────────────────────────────────────────────────────────────────────────

def _parse_topic(topic: str) -> dict | None:
    """
    Parse: aquasense/{network_id}/{zone_id}/{device_id}/{component}
    Returns None if the topic does not match the expected 5-segment structure.

    Example:
        "aquasense/building_a/kitchen_01/esp32_k1/outlet"
        → {"network_id": "building_a", "zone_id": "kitchen_01",
           "device_id": "esp32_k1", "component": "outlet"}
    """
    parts = topic.split("/")
    if len(parts) != 5 or parts[0] != "aquasense":
        logger.debug("Ignored non-AquaSense topic: %s", topic)
        return None

    _, network_id, zone_id, device_id, component = parts
    if not all([network_id, zone_id, device_id, component]):
        return None

    return {
        "network_id": network_id,   # MQTT string slug
        "zone_id":    zone_id,      # MQTT string slug
        "device_id":  device_id,
        "component":  component,    # "outlet" | "events" | "valve"
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Device validation  (with in-process cache)
# ─────────────────────────────────────────────────────────────────────────────

async def _validate_device(
    network_id: str,
    zone_id: str,
    device_id: str,
) -> Device | None:
    """
    Verify the device exists and belongs to the claimed network+zone.
    Uses a short-lived in-process cache so hot paths (100 msg/s) don't
    hit PostgreSQL on every message.

    Returns the Device ORM object, or None if not found / mismatch.
    """
    if device_id in _device_cache:
        return _device_cache[device_id]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Device)
            .join(Zone,    Device.zone_id    == Zone.id)
            .join(Network, Device.network_id == Network.id)
            .where(
                Device.device_id    == device_id,
                Zone.zone_id        == zone_id,
                Network.network_id  == network_id,
                Device.status       == "active",
            )
        )
        device = result.scalar_one_or_none()

    if device is None:
        logger.warning(
            "Unknown or mismatched device: network=%s zone=%s device=%s",
            network_id, zone_id, device_id,
        )

    _device_cache[device_id] = device   # cache None too to avoid repeat DB hits
    return device


# ─────────────────────────────────────────────────────────────────────────────
#  Buffer flush
# ─────────────────────────────────────────────────────────────────────────────

async def flush_buffer() -> None:
    """Bulk-insert buffered readings. ON CONFLICT DO NOTHING deduplicates."""
    async with _buffer_lock:
        if not _reading_buffer:
            return
        batch = _reading_buffer.copy()
        _reading_buffer.clear()

    async with AsyncSessionLocal() as db:
        try:
            stmt = (
                pg_insert(Reading)
                .values(batch)
                .on_conflict_do_nothing(constraint="uq_reading_device_ts")
            )
            await db.execute(stmt)
            await db.commit()
            logger.debug("Flushed %d readings", len(batch))
        except Exception as exc:
            logger.error("Batch insert failed: %s", exc)
            await db.rollback()


async def periodic_flush() -> None:
    """Background task: flush buffer every INSERT_BATCH_FLUSH_SECONDS."""
    while True:
        await asyncio.sleep(settings.INSERT_BATCH_FLUSH_SECONDS)
        await flush_buffer()


# ─────────────────────────────────────────────────────────────────────────────
#  Message processors
# ─────────────────────────────────────────────────────────────────────────────

async def _process_outlet_reading(parsed: dict, payload: dict) -> None:
    """
    Handle an outlet sensor reading:
      1. Validate device exists and belongs to claimed network/zone
      2. Buffer the reading row (with denormalised network_id, zone_id, sensor_type)
      3. Update device.last_seen
      4. Run backend-side leak evaluation
    """
    network_id = parsed["network_id"]
    zone_id    = parsed["zone_id"]
    device_id  = parsed["device_id"]

    device = await _validate_device(network_id, zone_id, device_id)
    if device is None:
        return

    try:
        flow_rate    = float(payload["flow_rate"])
        total_volume = float(payload["total_volume"])
        valve_status = str(payload.get("valve_status", "open"))
        timestamp    = datetime.fromisoformat(
            payload["timestamp"].replace("Z", "+00:00")
        )
    except (KeyError, ValueError) as exc:
        logger.warning("Malformed outlet payload device=%s: %s", device_id, exc)
        return

    reading_row = dict(
        device_id    = device_id,
        network_id   = network_id,   # denormalised MQTT slug
        zone_id      = zone_id,      # denormalised MQTT slug
        sensor_type  = "outlet",
        flow_rate    = flow_rate,
        total_volume = total_volume,
        valve_status = valve_status,
        timestamp    = timestamp,
    )

    async with _buffer_lock:
        _reading_buffer.append(reading_row)
        should_flush = len(_reading_buffer) >= settings.INSERT_BATCH_SIZE

    # Update heartbeat outside the buffer lock — non-blocking fire-and-forget
    asyncio.create_task(_touch_device(device_id))

    if should_flush:
        await flush_buffer()

    # Leak evaluation runs on every outlet reading (not batched)
    await evaluate_reading(
        device_id    = device_id,
        network_id   = network_id,
        zone_id      = zone_id,
        flow_rate    = flow_rate,
        total_volume = total_volume,
        timestamp    = timestamp,
    )

    # Flow mismatch check: compare latest inlet vs this outlet reading
    # Fetch the most recent inlet reading for the same zone to detect delta leaks.
    asyncio.create_task(
        _check_flow_mismatch(device, network_id, zone_id, device_id, flow_rate, timestamp)
    )

    logger.debug(
        "OUTLET device=%s flow=%.2f vol=%.2f valve=%s",
        device_id, flow_rate, total_volume, valve_status,
    )


async def _check_flow_mismatch(
    device,
    network_id:  str,
    zone_id:     str,
    device_id:   str,
    outlet_flow: float,
    timestamp,
) -> None:
    """
    Fetch the most recent inlet reading for the same zone and compare with
    the outlet flow rate. Calls evaluate_flow_mismatch() if inlet data exists.

    This runs as a fire-and-forget task so it never blocks the MQTT message loop.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Find the latest inlet reading in this zone (by zone integer PK)
            inlet_result = await db.execute(
                select(Reading.flow_rate)
                .join(Device, Reading.device_id == Device.device_id)
                .where(
                    Device.zone_id      == device.zone_id,   # integer PK
                    Reading.sensor_type == "inlet",
                )
                .order_by(Reading.timestamp.desc())
                .limit(1)
            )
            inlet_row = inlet_result.one_or_none()
            if inlet_row is None:
                return   # No inlet sensor data — skip mismatch check

            inlet_flow = float(inlet_row.flow_rate)

        await evaluate_flow_mismatch(
            zone_pk          = device.zone_id,
            network_id       = network_id,
            zone_id          = zone_id,
            inlet_flow       = inlet_flow,
            outlet_flow      = outlet_flow,
            outlet_device_id = device_id,
            timestamp        = timestamp,
        )
    except Exception as exc:
        logger.debug("Flow mismatch check failed for device=%s: %s", device_id, exc)


async def _process_event_message(parsed: dict, payload: dict) -> None:
    """
    Handle an event message published by the device on the /events component.
    Stores leak_detected / valve_opened / valve_closed events in the events table.

    Expected payload:
    {
        "event_type":  "leak_detected",
        "severity":    "high",
        "description": "Inlet flow 23L/min, outlet 8L/min — delta 15L/min",
        "timestamp":   "2026-02-26T14:00:00Z"
    }
    """
    network_id = parsed["network_id"]
    zone_id    = parsed["zone_id"]
    device_id  = parsed["device_id"]

    device = await _validate_device(network_id, zone_id, device_id)
    if device is None:
        return

    try:
        event_type  = str(payload["event_type"])
        severity    = str(payload.get("severity", "medium"))
        description = str(payload.get("description", ""))
        timestamp   = datetime.fromisoformat(
            payload.get("timestamp", datetime.now(timezone.utc).isoformat())
            .replace("Z", "+00:00")
        )
    except (KeyError, ValueError) as exc:
        logger.warning("Malformed event payload device=%s: %s", device_id, exc)
        return

    async with AsyncSessionLocal() as db:
        # Dedup: don't create a duplicate unresolved leak event within 60s
        if event_type == "leak_detected":
            recent = await db.execute(
                select(Event)
                .where(
                    Event.device_id  == device_id,
                    Event.event_type == "leak_detected",
                    Event.resolved   == False,
                    Event.timestamp  >= datetime.fromtimestamp(
                        timestamp.timestamp() - 60, tz=timezone.utc
                    ),
                )
                .limit(1)
            )
            if recent.scalar_one_or_none():
                return   # duplicate — skip

        event = Event(
            device_id   = device_id,
            network_id  = device.network_id,
            zone_id     = device.zone_id,
            event_type  = event_type,
            severity    = severity,
            description = description,
            timestamp   = timestamp,
        )
        db.add(event)

        # Auto-close valve in DB state for high-severity leaks
        if (
            event_type == "leak_detected"
            and severity == "high"
            and getattr(settings, "AUTO_CLOSE_VALVE_ON_HIGH", False)
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

        await db.commit()
    logger.info("EVENT device=%s type=%s severity=%s", device_id, event_type, severity)


async def _touch_device(device_id: str) -> None:
    """Update device.last_seen to now. Non-critical — errors are logged, not raised."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Device)
                .where(Device.device_id == device_id)
                .values(last_seen=datetime.now(timezone.utc))
            )
            await db.commit()
    except Exception as exc:
        logger.debug("last_seen update failed for %s: %s", device_id, exc)


# ─────────────────────────────────────────────────────────────────────────────
#  Main message dispatcher
# ─────────────────────────────────────────────────────────────────────────────

async def _dispatch(topic: str, raw_payload: bytes) -> None:
    """Route an incoming MQTT message to the correct handler."""
    parsed = _parse_topic(topic)
    if parsed is None:
        return

    try:
        payload = json.loads(raw_payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        logger.warning("Non-JSON payload on %s: %s", topic, raw_payload[:120])
        return

    component = parsed["component"]

    if component == "outlet":
        await _process_outlet_reading(parsed, payload)
    elif component == "events":
        await _process_event_message(parsed, payload)
    else:
        logger.debug("Unhandled component '%s' on topic %s", component, topic)


# ─────────────────────────────────────────────────────────────────────────────
#  Outbound valve publisher
# ─────────────────────────────────────────────────────────────────────────────

async def _outbound_loop(client: aiomqtt.Client, publish_queue: asyncio.Queue) -> None:
    """
    Drain the publish_queue and send valve commands over MQTT.
    Queue items are 4-tuples: (network_id, zone_id, device_id, action)
    Topic: aquasense/{network_id}/{zone_id}/{device_id}/valve
    """
    while True:
        item = await publish_queue.get()

        # Support both old (device_id, action) and new (network_id, zone_id, device_id, action)
        if len(item) == 4:
            network_id, zone_id, device_id, action = item
        elif len(item) == 2:
            # Legacy fallback — look up network/zone from DB
            device_id, action = item
            device = await _validate_device_by_id(device_id)
            if device is None:
                continue
            network_id = device.zone.network.network_id
            zone_id    = device.zone.zone_id
        else:
            logger.error("Invalid publish_queue item: %s", item)
            continue

        topic   = f"aquasense/{network_id}/{zone_id}/{device_id}/valve"
        message = json.dumps({"valve": action})
        try:
            await client.publish(topic, message, qos=1)
            logger.info("VALVE CMD → %s action=%s", topic, action)
        except Exception as exc:
            logger.error("Failed to publish valve command: %s", exc)


async def _validate_device_by_id(device_id: str) -> Device | None:
    """Fallback lookup when only device_id is known (legacy support)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Device)
            .where(Device.device_id == device_id)
            .options()   # add joinedload(Device.zone) if needed
        )
        return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
#  MQTT listener entry point
# ─────────────────────────────────────────────────────────────────────────────

async def start_mqtt_listener(publish_queue: asyncio.Queue) -> None:
    """
    Connect to HiveMQ Cloud over TLS and subscribe to:
        aquasense/+/+/+/outlet   — all outlet readings from all devices
        aquasense/+/+/+/events   — all device-reported events

    Auto-reconnects on disconnect with 5s back-off.
    """
    logger.info(
        "Connecting to HiveMQ at %s:%d",
        settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT,
    )

    while True:   # auto-reconnect loop
        try:
            async with aiomqtt.Client(
                hostname   = settings.MQTT_BROKER_HOST,
                port       = settings.MQTT_BROKER_PORT,
                identifier = settings.MQTT_CLIENT_ID,
                username   = settings.MQTT_USERNAME,
                password   = settings.MQTT_PASSWORD,
                tls_params = aiomqtt.TLSParameters(),
            ) as client:

                # Subscribe with wildcards — matches ALL networks/zones/devices
                await client.subscribe("aquasense/+/+/+/outlet", qos=1)
                await client.subscribe("aquasense/+/+/+/events", qos=1)
                logger.info("✅ MQTT connected — subscribed to outlet + events topics")

                # Outbound valve commands run concurrently
                asyncio.create_task(_outbound_loop(client, publish_queue))

                async for message in client.messages:
                    asyncio.create_task(
                        _dispatch(str(message.topic), message.payload)
                    )

        except aiomqtt.MqttError as exc:
            logger.error("MQTT disconnected: %s — retrying in 5s", exc)
            await asyncio.sleep(5)