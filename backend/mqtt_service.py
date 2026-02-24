# app/mqtt_service.py
# AquaSense v2 – HiveMQ subscriber with batch insert and leak detection

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List

import aiomqtt
from sqlalchemy import insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Device, Reading, Event, ValveLog
from app.leak_service import evaluate_reading

logger = logging.getLogger("aquasense.mqtt")

# ── Batch buffer ──────────────────────────────────────────────────────────────
_reading_buffer: List[dict] = []
_buffer_lock = asyncio.Lock()


async def flush_buffer() -> None:
    """Flush buffered readings to PostgreSQL using bulk insert."""
    async with _buffer_lock:
        if not _reading_buffer:
            return
        batch = _reading_buffer.copy()
        _reading_buffer.clear()

    async with AsyncSessionLocal() as db:
        try:
            # ON CONFLICT DO NOTHING prevents duplicate readings
            stmt = pg_insert(Reading).values(batch).on_conflict_do_nothing(
                constraint="uq_reading_device_ts"
            )
            await db.execute(stmt)
            await db.commit()
            logger.debug("Flushed %d readings to PostgreSQL", len(batch))
        except Exception as exc:
            logger.error("Batch insert failed: %s", exc)
            await db.rollback()


async def periodic_flush() -> None:
    """Background task: flush buffer every N seconds."""
    while True:
        await asyncio.sleep(settings.INSERT_BATCH_FLUSH_SECONDS)
        await flush_buffer()


async def process_message(payload: dict) -> None:
    """
    Parse sensor JSON, buffer the reading, and run leak detection.

    Expected payload:
    {
        "network_id": "network_1",
        "device_id":  "device_101",
        "flow_rate":  12.5,
        "total_volume": 2034.2,
        "valve_status": "open",
        "timestamp":  "2026-02-24T10:30:00Z"
    }
    """
    device_id    = payload["device_id"]
    flow_rate    = float(payload["flow_rate"])
    total_volume = float(payload["total_volume"])
    valve_status = str(payload.get("valve_status", "open"))
    timestamp    = datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

    # Buffer reading for batch insert
    reading_row = dict(
        device_id=device_id,
        flow_rate=flow_rate,
        total_volume=total_volume,
        valve_status=valve_status,
        timestamp=timestamp,
    )
    async with _buffer_lock:
        _reading_buffer.append(reading_row)
        should_flush = len(_reading_buffer) >= settings.INSERT_BATCH_SIZE

    if should_flush:
        await flush_buffer()

    # Leak detection runs on every reading (outside batch — needs async DB)
    await evaluate_reading(device_id, flow_rate, total_volume, timestamp)


async def start_mqtt_listener(publish_queue: asyncio.Queue) -> None:
    """Connect to HiveMQ Cloud (TLS) and subscribe to all device reading topics."""
    logger.info("Connecting to HiveMQ at %s:%d", settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT)

    while True:  # auto-reconnect
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_BROKER_HOST,
                port=settings.MQTT_BROKER_PORT,
                identifier=settings.MQTT_CLIENT_ID,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
                tls_params=aiomqtt.TLSParameters(),  # HiveMQ Cloud requires TLS
            ) as client:
                await client.subscribe(settings.MQTT_TOPIC_READINGS)
                logger.info("Subscribed to %s", settings.MQTT_TOPIC_READINGS)

                async def outbound_loop():
                    while True:
                        device_id, action = await publish_queue.get()
                        topic = settings.MQTT_TOPIC_VALVE.format(device_id=device_id)
                        await client.publish(topic, json.dumps({"valve": action}))

                asyncio.create_task(outbound_loop())

                async for message in client.messages:
                    try:
                        payload = json.loads(message.payload.decode())
                        await process_message(payload)
                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        logger.warning("Bad MQTT payload: %s | error: %s", message.payload[:200], exc)

        except aiomqtt.MqttError as exc:
            logger.error("MQTT disconnected: %s — retrying in 5s", exc)
            await asyncio.sleep(5)
