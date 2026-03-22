# mqtt_service.py
# AquaSense v3.2 — Async MQTT service
#
# Topic structure (v3.2):
#   aquasense/{network_id}/{zone_id}/{device_id}/sensor/{location}/{type}
#   aquasense/{network_id}/{zone_id}/{device_id}/valve/{type}
#   aquasense/{network_id}/{zone_id}/{device_id}/leak/{type}
#
# Subscriptions:
#   aquasense/+/+/+/sensor/+/+   — inlet and outlet sensor readings
#   aquasense/+/+/+/leak/+       — device-reported leak alerts
#
# Valve publish:
#   aquasense/{network_id}/{zone_id}/{device_id}/valve/command
#
# Changes from v3.1:
#   • parse_topic() updated for new 6-7 segment structure (category + location + type)
#   • _dispatch() routes on category+location instead of component
#   • _process_outlet_reading() and _process_inlet_reading() both called from sensor handler
#   • _process_inlet_reading() added — stores inlet readings and triggers mismatch check
#   • _process_event_message() now triggered by category == "leak", type == "alert"
#   • _outbound_loop() topic updated: .../valve → .../valve/command
#   • Subscriptions updated to match new wildcard patterns
#   • Legacy 2-tuple and _validate_device_by_id() removed — all queues use 4-tuples

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
from models import Device, Network, Zone, Reading, Event, ValveLog, ValveState
from leak_service import LeakDetectionService, get_leak_service

logger = logging.getLogger("aquasense.mqtt")

# ─── Batch write buffer ───────────────────────────────────────────────────────
_reading_buffer: list[dict] = []
_buffer_lock = asyncio.Lock()

# ─── In-process device cache (TTL = 60 seconds) ──────────────────────────────
# Stores (Device | None, cached_at: datetime) per device_id.
# None is cached too — avoids repeat DB hits for unknown devices.
# TTL prevents stale entries when a device is disabled, moved, or deleted.
_DEVICE_CACHE_TTL_SECONDS = 60
_device_cache: dict[str, tuple[Optional[Device], datetime]] = {}

# ─── Leak detection service — injected by main.py ────────────────────────────
_leak_service: Optional[LeakDetectionService] = None


def set_leak_service(svc: LeakDetectionService) -> None:
    global _leak_service
    _leak_service = svc


def invalidate_device_cache(device_id: str) -> None:
    """Called by device_router after registering, updating, or deleting a device."""
    _device_cache.pop(device_id, None)


# ─────────────────────────────────────────────────────────────────────────────
#  Topic parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_topic(topic: str) -> dict | None:
    """
    Parse the new 6-7 segment topic structure.

    Sensor:  aquasense/{network}/{zone}/{device}/sensor/{location}/{type}
             location = inlet | outlet
             type     = flow_rate | total_L | heartbeat | live_flow

    Valve:   aquasense/{network}/{zone}/{device}/valve/{type}
             type     = command | status

    Leak:    aquasense/{network}/{zone}/{device}/leak/{type}
             type     = alert

    Returns None for anything that does not match a known pattern.
    """
    parts = topic.split("/")

    if len(parts) < 6 or parts[0] != "aquasense":
        logger.debug("Ignored non-AquaSense topic: %s", topic)
        return None

    network_id = parts[1]
    zone_id    = parts[2]
    device_id  = parts[3]
    category   = parts[4]

    if not all([network_id, zone_id, device_id, category]):
        return None

    result = {
        "network_id": network_id,
        "zone_id":    zone_id,
        "device_id":  device_id,
        "category":   category,
    }

    if category == "sensor" and len(parts) == 7:
        result["location"] = parts[5]   # inlet | outlet
        result["type"]     = parts[6]   # flow_rate | total_L | heartbeat | live_flow

    elif category == "valve" and len(parts) == 6:
        result["type"] = parts[5]       # command | status

    elif category == "leak" and len(parts) == 6:
        result["type"] = parts[5]       # alert

    else:
        logger.debug("Unrecognised topic pattern: %s", topic)
        return None

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Device validation  (with in-process cache)
# ─────────────────────────────────────────────────────────────────────────────

async def _validate_device(
    network_id: str,
    zone_id:    str,
    device_id:  str,
    expected_sensor_type: Optional[str] = None,
) -> Device | None:
    """
    Verify the device exists and belongs to the claimed network+zone.

    TTL cache: entries expire after _DEVICE_CACHE_TTL_SECONDS (60s).
    This ensures disabled, moved, or deleted devices are not served
    from stale cache for more than one minute.

    If expected_sensor_type is provided ("inlet" or "outlet"), the device's
    sensor_type is validated against it. A mismatch is rejected so a device
    cannot corrupt data by publishing on the wrong topic type.
    """
    # Check TTL cache
    cached = _device_cache.get(device_id)
    if cached is not None:
        device, cached_at = cached
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age < _DEVICE_CACHE_TTL_SECONDS:
            # Cache hit — still validate sensor_type even from cache
            if device is not None and expected_sensor_type:
                if device.sensor_type != expected_sensor_type:
                    logger.warning(
                        "Device type mismatch (cached): device=%s sensor_type=%s expected=%s",
                        device_id, device.sensor_type, expected_sensor_type,
                    )
                    return None
            return device
        # Expired — fall through to DB
        _device_cache.pop(device_id, None)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Device)
            .join(Zone,    Device.zone_id    == Zone.id)
            .join(Network, Device.network_id == Network.id)
            .where(
                Device.device_id   == device_id,
                Zone.zone_id       == zone_id,
                Network.network_id == network_id,
                Device.status      == "active",
            )
        )
        device = result.scalar_one_or_none()

    if device is None:
        logger.warning(
            "Unknown or mismatched device: network=%s zone=%s device=%s",
            network_id, zone_id, device_id,
        )
        # Cache the None to avoid hammering DB for repeated unknown device messages
        _device_cache[device_id] = (None, datetime.now(timezone.utc))
        return None

    # Device type validation — reject if topic location doesn't match DB sensor_type
    if expected_sensor_type and device.sensor_type != expected_sensor_type:
        logger.warning(
            "Device type mismatch: device=%s sensor_type=%s tried to publish on '%s' topic — rejected",
            device_id, device.sensor_type, expected_sensor_type,
        )
        # Don't cache — let it re-check next time in case it was misconfigured temporarily
        return None

    _device_cache[device_id] = (device, datetime.now(timezone.utc))
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

# ─── Per-device value accumulators ───────────────────────────────────────────
# ESP32 publishes flow_rate and total_L on separate topics.
# We accumulate both values per device and only write a reading row once
# we have a complete pair for the same device within the same second.
# Key: device_id → {"flow_rate": float | None, "total_volume": float | None, "ts": datetime}
_outlet_accumulator: dict[str, dict] = {}
_inlet_accumulator:  dict[str, dict] = {}
_ACCUMULATOR_WINDOW_SECONDS = 2   # pair must arrive within this window


async def _process_outlet_reading(parsed: dict, msg_type: str, value: float) -> None:
    """
    Handle a single outlet sensor topic from the ESP32.

    ESP32 publishes flow and total on separate topics:
      .../sensor/outlet/flow_rate  → plain float e.g. "23.10"
      .../sensor/outlet/total_L    → plain float e.g. "1024.50"

    We accumulate both per device. Once we have a complete pair (both values
    arrived within _ACCUMULATOR_WINDOW_SECONDS), we write one reading row,
    run leak evaluation, and run the mismatch check.

    live_flow topics are accepted but not stored — they are read-only display
    values for the Flutter WaterStatusCard and do not affect the DB.
    """
    if msg_type == "live_flow":
        return   # display-only — not stored

    if msg_type not in ("flow_rate", "total_L"):
        logger.debug("Unhandled outlet msg_type '%s'", msg_type)
        return

    network_id = parsed["network_id"]
    zone_id    = parsed["zone_id"]
    device_id  = parsed["device_id"]

    device = await _validate_device(network_id, zone_id, device_id, expected_sensor_type="outlet")
    if device is None:
        return

    now = datetime.now(timezone.utc)

    # Initialise or reset accumulator if the previous window has expired
    acc = _outlet_accumulator.get(device_id)
    if acc is None or (now - acc["ts"]).total_seconds() > _ACCUMULATOR_WINDOW_SECONDS:
        acc = {"flow_rate": None, "total_volume": None, "ts": now}
        _outlet_accumulator[device_id] = acc

    if msg_type == "flow_rate":
        acc["flow_rate"] = value
    elif msg_type == "total_L":
        acc["total_volume"] = value

    # Not a complete pair yet — wait for the other topic to arrive
    if acc["flow_rate"] is None or acc["total_volume"] is None:
        return

    # Complete pair — extract values and clear accumulator
    flow_rate    = acc["flow_rate"]
    total_volume = acc["total_volume"]
    timestamp    = acc["ts"]
    _outlet_accumulator.pop(device_id, None)

    # valve_state comes from the DB (device record) — ESP32 doesn't send it
    valve_status = device.valve_state or "open"

    reading_row = dict(
        device_id    = device_id,
        network_id   = network_id,
        zone_id      = zone_id,
        sensor_type  = "outlet",
        flow_rate    = flow_rate,
        total_volume = total_volume,
        valve_status = valve_status,
        timestamp    = timestamp,
    )

    async with _buffer_lock:
        _reading_buffer.append(reading_row)
        should_flush = len(_reading_buffer) >= settings.INSERT_BATCH_SIZE

    asyncio.create_task(_touch_device(device_id))

    if should_flush:
        await flush_buffer()

    # Notify leak service — sync valve state first, then update flow
    if _leak_service:
        await _leak_service.update_valve_state(device.zone_id, ValveState(valve_status))
        await _leak_service.update_outlet_flow(device.zone_id, flow_rate)

    logger.debug(
        "OUTLET device=%s flow=%.2f vol=%.2f valve=%s",
        device_id, flow_rate, total_volume, valve_status,
    )


async def _process_inlet_reading(parsed: dict, msg_type: str, value: float) -> None:
    """
    Handle a single inlet sensor topic from the ESP32.

    ESP32 publishes:
      .../sensor/inlet/flow_rate  → plain float
      .../sensor/inlet/total_L    → plain float (optional on some firmware)

    Inlet readings are stored for flow mismatch checks triggered by the
    next outlet reading from the same zone. No direct leak evaluation here.
    """
    if msg_type == "live_flow":
        return   # display-only

    if msg_type not in ("flow_rate", "total_L"):
        logger.debug("Unhandled inlet msg_type '%s'", msg_type)
        return

    network_id = parsed["network_id"]
    zone_id    = parsed["zone_id"]
    device_id  = parsed["device_id"]

    device = await _validate_device(network_id, zone_id, device_id, expected_sensor_type="inlet")
    if device is None:
        return

    now = datetime.now(timezone.utc)

    acc = _inlet_accumulator.get(device_id)
    if acc is None or (now - acc["ts"]).total_seconds() > _ACCUMULATOR_WINDOW_SECONDS:
        acc = {"flow_rate": None, "total_volume": None, "ts": now}
        _inlet_accumulator[device_id] = acc

    if msg_type == "flow_rate":
        acc["flow_rate"] = value
    elif msg_type == "total_L":
        acc["total_volume"] = value

    # Only need flow_rate to write an inlet row — total_L is optional for inlet
    if acc["flow_rate"] is None:
        return

    flow_rate    = acc["flow_rate"]
    total_volume = acc["total_volume"] or 0.0
    timestamp    = acc["ts"]
    _inlet_accumulator.pop(device_id, None)

    reading_row = dict(
        device_id    = device_id,
        network_id   = network_id,
        zone_id      = zone_id,
        sensor_type  = "inlet",
        flow_rate    = flow_rate,
        total_volume = total_volume,
        valve_status = None,
        timestamp    = timestamp,
    )

    async with _buffer_lock:
        _reading_buffer.append(reading_row)
        should_flush = len(_reading_buffer) >= settings.INSERT_BATCH_SIZE

    asyncio.create_task(_touch_device(device_id))

    if should_flush:
        await flush_buffer()

    # Notify leak service — inlet flow update triggers leak evaluation
    if _leak_service:
        await _leak_service.update_inlet_flow(device.zone_id, flow_rate)

    logger.debug("INLET device=%s flow=%.2f", device_id, flow_rate)


async def _process_event_message(parsed: dict, payload: dict) -> None:
    """
    Handle a leak alert published by the device on .../leak/alert.
    Stores the event in the events table and optionally auto-closes the valve.

    ESP32 payload (what the device actually sends):
    {
        "status":       "LEAK_DETECTED",   ← uppercase string
        "valve":        "CLOSED",          ← current valve state from device
        "inlet_flow":   23.1,              ← L/min
        "outlet_flow":  8.0               ← L/min
    }

    We normalise this into our internal format before storing.
    """
    network_id = parsed["network_id"]
    zone_id    = parsed["zone_id"]
    device_id  = parsed["device_id"]

    device = await _validate_device(network_id, zone_id, device_id)
    if device is None:
        return

    try:
        # ── Normalise ESP32 payload ───────────────────────────────────────
        status      = str(payload.get("status", "")).upper()
        inlet_flow  = float(payload.get("inlet_flow",  0.0))
        outlet_flow = float(payload.get("outlet_flow", 0.0))
        delta       = inlet_flow - outlet_flow

        # Map ESP32 status string → internal event_type
        STATUS_MAP = {
            "LEAK_DETECTED": "leak_detected",
            "FLOW_MISMATCH": "flow_mismatch",
        }
        event_type = STATUS_MAP.get(status, "leak_detected")

        description = (
            f"Device reported {status}: "
            f"inlet {inlet_flow:.2f} L/min, outlet {outlet_flow:.2f} L/min "
            f"(delta {delta:.2f} L/min)."
        )

        # Timestamp — ESP32 may or may not include one; fall back to server time
        raw_ts    = payload.get("timestamp")
        timestamp = (
            datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if raw_ts
            else datetime.now(timezone.utc)
        )

    except (TypeError, ValueError) as exc:
        logger.warning("Malformed leak alert payload device=%s: %s", device_id, exc)
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
                return

        event = Event(
            device_id   = device_id,
            network_id  = device.network_id,
            zone_id     = device.zone_id,
            event_type  = event_type,
            description = description,
            timestamp   = timestamp,
        )
        db.add(event)

        # Auto-close on high delta when valve is open
        if (
            event_type == "leak_detected"
            and delta >= settings.LEAK_SEVERITY_HIGH
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
    logger.info("EVENT device=%s type=%s", device_id, event_type)


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
    """
    Route an incoming MQTT message to the correct handler.

    ESP32 publishes sensor values as plain floats on individual topics
    (e.g. "23.10"), not as JSON objects. Leak alerts are JSON objects.
    We decode per category+type rather than always json.loads().
    """
    parsed = parse_topic(topic)
    if parsed is None:
        return

    category  = parsed["category"]
    msg_type  = parsed.get("type", "")
    location  = parsed.get("location", "")
    raw_text  = raw_payload.decode("utf-8", errors="replace").strip()

    # ── Sensor messages — ESP32 publishes a plain float value ────────────
    if category == "sensor":

        # Heartbeat — no value needed, just touch last_seen and exit
        if msg_type == "heartbeat":
            asyncio.create_task(_touch_device(parsed["device_id"]))
            # Also notify leak service so outlet-alive check stays current
            if _leak_service:
                device = await _validate_device(
                    parsed["network_id"], parsed["zone_id"], parsed["device_id"],
                    expected_sensor_type="outlet",
                )
                if device:
                    asyncio.create_task(
                        _leak_service.update_outlet_heartbeat(device.zone_id)
                    )
            logger.debug("HEARTBEAT device=%s", parsed["device_id"])
            return

        # For all other sensor types, the payload is a plain float string
        try:
            value = float(raw_text)
        except ValueError:
            logger.warning(
                "Non-numeric sensor payload on %s: %r", topic, raw_text[:60]
            )
            return

        if location == "outlet":
            await _process_outlet_reading(parsed, msg_type, value)
        elif location == "inlet":
            await _process_inlet_reading(parsed, msg_type, value)
        else:
            logger.debug("Unknown sensor location '%s' on topic %s", location, topic)

    # ── Leak alert — ESP32 publishes a JSON object ────────────────────────
    elif category == "leak":
        if msg_type == "alert":
            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.warning("Non-JSON leak payload on %s: %r", topic, raw_text[:120])
                return
            await _process_event_message(parsed, payload)
        else:
            logger.debug("Unhandled leak type '%s' on topic %s", msg_type, topic)

    # ── Valve status — acknowledgement from device, log only ─────────────
    elif category == "valve":
        if msg_type == "status":
            logger.info(
                "VALVE STATUS from device=%s payload=%r",
                parsed["device_id"], raw_text,
            )
        else:
            logger.debug("Unhandled valve type '%s' on topic %s", msg_type, topic)

    else:
        logger.debug("Unhandled category '%s' on topic %s", category, topic)


# ─────────────────────────────────────────────────────────────────────────────
#  Outbound valve publisher
# ─────────────────────────────────────────────────────────────────────────────

async def _outbound_loop(client: aiomqtt.Client, publish_queue: asyncio.Queue) -> None:
    """
    Drain the publish_queue and send valve commands over MQTT.
    Queue items are 4-tuples: (network_id, zone_id, device_id, action)

    Topic: aquasense/{network_id}/{zone_id}/{device_id}/valve/command
    """
    while True:
        item = await publish_queue.get()

        if len(item) != 4:
            logger.error("Invalid publish_queue item (expected 4-tuple): %s", item)
            continue

        network_id, zone_id, device_id, action = item
        topic   = f"aquasense/{network_id}/{zone_id}/{device_id}/valve/command"
        message = json.dumps({"valve": action})

        try:
            await client.publish(topic, message, qos=1)
            logger.info("VALVE CMD → %s action=%s", topic, action)
        except Exception as exc:
            logger.error("Failed to publish valve command: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
#  MQTT listener entry point
# ─────────────────────────────────────────────────────────────────────────────

async def start_mqtt_listener(publish_queue: asyncio.Queue) -> None:
    logger.info(
        "Connecting to HiveMQ at %s:%d",
        settings.MQTT_BROKER_HOST,
        settings.MQTT_BROKER_PORT,
    )

    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_BROKER_HOST,
                port=settings.MQTT_BROKER_PORT,
                identifier=settings.MQTT_CLIENT_ID,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
                tls_params=aiomqtt.TLSParameters(),
                keepalive=60,
            ) as client:

                async with client.unfiltered_messages() as messages:
                    await client.subscribe("aquasense/+/+/+/sensor/+/+", qos=1)
                    await client.subscribe("aquasense/+/+/+/leak/+", qos=1)

                    logger.info(
                        "✅ MQTT connected — subscribed to sensor (inlet+outlet) + leak topics"
                    )

                    # Start outbound publisher loop
                    asyncio.create_task(_outbound_loop(client, publish_queue))

                    async for message in messages:
                        asyncio.create_task(
                            _dispatch(str(message.topic), message.payload)
                        )

        except aiomqtt.MqttError as exc:
            logger.error("MQTT disconnected: %s — retrying in 5s", exc)
            await asyncio.sleep(5)