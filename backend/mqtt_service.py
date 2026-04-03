# mqtt_service.py
# AquaSense v3.3 — Async MQTT service
#
# Topic structure (v3.2+):
#   aquasense/{network_id}/{zone_id}/{device_id}/sensor/{location}/{type}
#   aquasense/{network_id}/{zone_id}/{device_id}/valve/{type}
#   aquasense/{network_id}/{zone_id}/{device_id}/leak/{type}
#
# Subscriptions:
#   aquasense/+/+/+/sensor/+/+   — inlet and outlet sensor readings
#   aquasense/+/+/+/leak/+       — device-reported leak alerts
#   aquasense/+/+/+/valve/+      — valve status acknowledgements from ESP32  ← NEW v3.3
#
# Valve publish:
#   aquasense/{network_id}/{zone_id}/{device_id}/valve/command
#   Payload: plain text "open" or "close"   ← FIXED v3.3 (was JSON {"valve": action})
#
# v3.3 changes (scenario fixes):
#   • _outbound_loop: sends plain "open"/"close" instead of JSON.
#     The ESP32 callback does `if (message == "open")` — it expects plain text.
#   • _process_event_message: when ESP32 reports LEAK_DETECTED with valve=CLOSED,
#     the server now updates device.valve_state to "closed" in the DB so the
#     mobile app toggle reflects the actual physical state (Scenario 1 fix).
#   • _process_valve_status: new function that syncs device.valve_state from
#     ESP32's valve/status acknowledgement messages (Scenario 1 + 2 robustness).
#   • start_mqtt_listener: added subscription to aquasense/+/+/+/valve/+
#   • _dispatch: routes valve/status messages to _process_valve_status.

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
    Parse the 6-7 segment topic structure.

    Sensor:  aquasense/{network}/{zone}/{device}/sensor/{location}/{type}
    Valve:   aquasense/{network}/{zone}/{device}/valve/{type}
    Leak:    aquasense/{network}/{zone}/{device}/leak/{type}
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
    """Verify the device exists and belongs to the claimed network+zone. TTL-cached."""
    cached = _device_cache.get(device_id)
    if cached is not None:
        device, cached_at = cached
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age < _DEVICE_CACHE_TTL_SECONDS:
            if device is not None and expected_sensor_type:
                if device.sensor_type != expected_sensor_type:
                    logger.warning(
                        "Device type mismatch (cached): device=%s sensor_type=%s expected=%s",
                        device_id, device.sensor_type, expected_sensor_type,
                    )
                    return None
            return device
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
        _device_cache[device_id] = (None, datetime.now(timezone.utc))
        return None

    if expected_sensor_type and device.sensor_type != expected_sensor_type:
        logger.warning(
            "Device type mismatch: device=%s sensor_type=%s tried to publish on '%s' topic — rejected",
            device_id, device.sensor_type, expected_sensor_type,
        )
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
#  Per-device value accumulators
# ─────────────────────────────────────────────────────────────────────────────

_outlet_accumulator: dict[str, dict] = {}
_inlet_accumulator:  dict[str, dict] = {}
_ACCUMULATOR_WINDOW_SECONDS = 2


# ─────────────────────────────────────────────────────────────────────────────
#  Message processors
# ─────────────────────────────────────────────────────────────────────────────

async def _process_outlet_reading(parsed: dict, msg_type: str, value: float) -> None:
    """Handle a single outlet sensor topic from the ESP32."""
    if msg_type == "live_flow":
        return

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

    acc = _outlet_accumulator.get(device_id)
    if acc is None or (now - acc["ts"]).total_seconds() > _ACCUMULATOR_WINDOW_SECONDS:
        acc = {"flow_rate": None, "total_volume": None, "ts": now}
        _outlet_accumulator[device_id] = acc

    if msg_type == "flow_rate":
        acc["flow_rate"] = value
    elif msg_type == "total_L":
        acc["total_volume"] = value

    if acc["flow_rate"] is None or acc["total_volume"] is None:
        return

    flow_rate    = acc["flow_rate"]
    total_volume = acc["total_volume"]
    timestamp    = acc["ts"]
    _outlet_accumulator.pop(device_id, None)

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

    if _leak_service:
        # update_valve_state is NOT called here — the outlet device has no
        # valve. Valve state is owned by the inlet ESP32 and is updated in
        # _process_inlet_reading and _process_valve_status only.
        await _leak_service.update_outlet_flow(device.zone_id, flow_rate)

    logger.debug(
        "OUTLET device=%s flow=%.2f vol=%.2f valve=%s",
        device_id, flow_rate, total_volume, valve_status,
    )


async def _process_inlet_reading(parsed: dict, msg_type: str, value: float) -> None:
    """Handle a single inlet sensor topic from the ESP32."""
    if msg_type == "live_flow":
        return

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

    if _leak_service:
        # The inlet device owns the valve — its valve_state is authoritative.
        # Update the leak service here so it always reflects the physical valve
        # position, not a stale value from the outlet device record.
        await _leak_service.update_valve_state(
            device.zone_id,
            ValveState(device.valve_state or "open"),
        )
        await _leak_service.update_inlet_flow(device.zone_id, flow_rate)

    logger.debug("INLET device=%s flow=%.2f valve=%s", device_id, flow_rate, device.valve_state)


async def _process_event_message(parsed: dict, payload: dict) -> None:
    """
    Handle a leak alert published by the ESP32 on .../leak/alert.

    ESP32 payload:
    {
        "status":       "LEAK_DETECTED",
        "valve":        "CLOSED",
        "inlet_flow":   23.1,
        "outlet_flow":  8.0
    }

    v3.3 fix (Scenario 1):
    When the ESP32 reports LEAK_DETECTED and valve=CLOSED, the server now
    updates device.valve_state = "closed" in the DB immediately. This ensures
    the mobile app toggle shows the correct closed state without waiting for
    the next outlet sensor reading to carry the valve_state field.
    """
    network_id = parsed["network_id"]
    zone_id    = parsed["zone_id"]
    device_id  = parsed["device_id"]

    device = await _validate_device(network_id, zone_id, device_id)
    if device is None:
        return

    try:
        status      = str(payload.get("status", "")).upper()
        inlet_flow  = float(payload.get("inlet_flow",  0.0))
        outlet_flow = float(payload.get("outlet_flow", 0.0))
        delta       = inlet_flow - outlet_flow

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

        raw_ts    = payload.get("timestamp")
        timestamp = (
            datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if raw_ts
            else datetime.now(timezone.utc)
        )

        # ── Scenario 1: sync valve state from device report ───────────────
        # The ESP32 closes the valve autonomously on leak. It then publishes
        # this leak/alert message with valve="CLOSED". We update the DB record
        # here so that the mobile app toggle reflects reality immediately,
        # without waiting for the next outlet sensor reading.
        valve_from_esp = str(payload.get("valve", "")).upper()
        if valve_from_esp == "CLOSED" and event_type in ("leak_detected", "flow_mismatch"):
            valve_sync_state = "closed"
        elif valve_from_esp == "OPEN":
            valve_sync_state = "open"
        else:
            valve_sync_state = None   # don't overwrite if not reported

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
                logger.debug("Dedup: skipping duplicate leak event for device=%s", device_id)
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

        # ── Scenario 1: update device.valve_state so mobile toggle syncs ──
        if valve_sync_state is not None:
            await db.execute(
                update(Device)
                .where(Device.device_id == device_id)
                .values(valve_state=valve_sync_state)
            )
            logger.info(
                "VALVE SYNC from ESP32 leak report: device=%s → %s",
                device_id, valve_sync_state,
            )

        # Auto-close (high delta) — only if not already closed by ESP32 report above
        if (
            event_type == "leak_detected"
            and delta >= settings.LEAK_SEVERITY_HIGH
            and getattr(settings, "AUTO_CLOSE_VALVE_ON_HIGH", False)
            and valve_sync_state != "closed"   # avoid double-write
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

    # Sync leak service valve state to match DB
    if _leak_service and device.zone_id and valve_sync_state:
        vs = ValveState.CLOSED if valve_sync_state == "closed" else ValveState.OPEN
        await _leak_service.update_valve_state(device.zone_id, vs)

    logger.info("EVENT device=%s type=%s", device_id, event_type)


async def _process_valve_status(parsed: dict, status_text: str) -> None:
    """
    Handle valve/status acknowledgements published by the ESP32.

    The ESP32 publishes to TOPIC_VALVE_STATUS = .../valve/status after every
    valve open or close operation (both commanded and autonomous). The server
    uses this to keep device.valve_state in the DB in sync with the physical
    valve position.

    ESP32 publishes plain text: "Opened" or "Closed" (with retained=true).

    This provides a reliable sync path for both scenarios:
      Scenario 1: ESP32 auto-closes on leak → status "Closed" arrives here
      Scenario 2: User closes from app → server commands → ESP32 acks here
    """
    device_id = parsed["device_id"]

    device = await _validate_device(
        parsed["network_id"], parsed["zone_id"], device_id
    )
    if device is None:
        return

    # Normalise ESP32 text to our internal valve state
    text_lower = status_text.lower().strip()
    if "open" in text_lower:
        valve_state = "open"
        vs_enum     = ValveState.OPEN
    elif "close" in text_lower:
        valve_state = "closed"
        vs_enum     = ValveState.CLOSED
    else:
        logger.debug("Unrecognised valve status text from device=%s: %r", device_id, status_text)
        return

    # Update DB — only write if the state actually changed to avoid churn
    if device.valve_state != valve_state:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Device)
                .where(Device.device_id == device_id)
                .values(valve_state=valve_state)
            )
            await db.commit()
        logger.info(
            "VALVE STATUS ACK device=%s → %s (was %s)",
            device_id, valve_state, device.valve_state,
        )
    else:
        logger.debug(
            "VALVE STATUS ACK device=%s state unchanged (%s)", device_id, valve_state
        )

    # Sync leak service in all cases (state may have drifted in memory)
    if _leak_service and device.zone_id:
        await _leak_service.update_valve_state(device.zone_id, vs_enum)

    # Invalidate cache so next read picks up the updated valve_state
    invalidate_device_cache(device_id)


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

    ESP32 publishes sensor values as plain floats on individual topics.
    Leak alerts and valve status are plain text or JSON.
    """
    parsed = parse_topic(topic)
    if parsed is None:
        return

    category  = parsed["category"]
    msg_type  = parsed.get("type", "")
    location  = parsed.get("location", "")
    raw_text  = raw_payload.decode("utf-8", errors="replace").strip()

    # ── Sensor messages ───────────────────────────────────────────────────
    if category == "sensor":

        if msg_type == "heartbeat":
            asyncio.create_task(_touch_device(parsed["device_id"]))
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

    # ── Leak alert ────────────────────────────────────────────────────────
    elif category == "leak":
        if msg_type == "alert":
            # Handle plain "Normal" status (not JSON) — ESP32 sends this on clear
            if raw_text.strip().lower() in ("normal", "\"normal\""):
                logger.debug("LEAK CLEAR signal device=%s", parsed["device_id"])
                return

            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.warning("Non-JSON leak payload on %s: %r", topic, raw_text[:120])
                return
            await _process_event_message(parsed, payload)
        else:
            logger.debug("Unhandled leak type '%s' on topic %s", msg_type, topic)

    # ── Valve status acknowledgement from ESP32 ───────────────────────────
    elif category == "valve":
        if msg_type == "status":
            # Scenario 1 + 2: ESP32 acks its valve state after every change.
            # Use this to keep device.valve_state in the DB accurate.
            await _process_valve_status(parsed, raw_text)
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

    Topic:   aquasense/{network_id}/{zone_id}/{device_id}/valve/command
    Payload: plain text "open" or "close"

    v3.3 fix: payload changed from JSON {"valve": action} to plain text.
    The ESP32 mqttCallback does:
        if (message == "open") { ... }
        else if (message == "close") { ... }
    It compares the raw string directly, so JSON encoding broke valve commands.

    v3.3 fix: on publish failure the item is put BACK into the queue and this
    loop exits. When start_mqtt_listener reconnects it starts a fresh
    _outbound_loop which will pick up and retry the queued item. Without this,
    a command queued during a brief MQTT disconnect was silently lost forever.
    """
    while True:
        item = await publish_queue.get()

        if len(item) != 4:
            logger.error("Invalid publish_queue item (expected 4-tuple): %s", item)
            continue

        network_id, zone_id, device_id, action = item
        topic   = f"aquasense/{network_id}/{zone_id}/{device_id}/valve/command"

        # Send plain text so ESP32 can compare directly with == "open" / == "close"
        message = action   # "open" or "close"

        try:
            await client.publish(topic, message, qos=1)
            logger.info("VALVE CMD → %s action=%s", topic, action)
        except Exception as exc:
            logger.error(
                "Failed to publish valve command to %s — re-queuing for retry: %s",
                topic, exc,
            )
            # Put the item back so it is retried on the next MQTT connection.
            # Exit this loop — start_mqtt_listener will create a new _outbound_loop
            # once the connection is re-established.
            await publish_queue.put(item)
            return


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
                    await client.subscribe("aquasense/+/+/+/leak/+",      qos=1)
                    await client.subscribe("aquasense/+/+/+/valve/+",     qos=1)  # v3.3: valve status ack

                    logger.info(
                        "✅ MQTT connected — subscribed to sensor (inlet+outlet) + leak + valve topics"
                    )

                    asyncio.create_task(_outbound_loop(client, publish_queue))

                    async for message in messages:
                        asyncio.create_task(
                            _dispatch(str(message.topic), message.payload)
                        )

        except aiomqtt.MqttError as exc:
            logger.error("MQTT disconnected: %s — retrying in 5s", exc)
            await asyncio.sleep(5)