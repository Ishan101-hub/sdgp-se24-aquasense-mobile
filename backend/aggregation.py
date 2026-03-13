# aggregation.py
# AquaSense v3 – Daily summary aggregation
# Run as a background task (every midnight) via schedule_aggregation()

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import AsyncSessionLocal
from models import Device, Zone, Network, Reading, DailySummary, Event

logger = logging.getLogger("aquasense.aggregation")


async def _get_device_slugs(device_id: str, db) -> tuple[str, str]:
    """
    Fetch the MQTT string slugs (network_id, zone_id) for a device.
    These are the denormalised string values stored on Reading/DailySummary rows —
    NOT the integer PKs.

    Returns ("unknown", "unknown") if device is not found so aggregation
    still runs rather than crashing the nightly job.
    """
    result = await db.execute(
        select(Network.network_id, Zone.zone_id)
        .join(Zone,    Device.zone_id    == Zone.id)
        .join(Network, Zone.network_id   == Network.id)
        .where(Device.device_id == device_id)
    )
    row = result.one_or_none()
    if row is None:
        logger.warning("Device %s not found — slugs defaulting to 'unknown'", device_id)
        return ("unknown", "unknown")
    return (row.network_id, row.zone_id)


async def compute_daily_summary(device_id: str, target_date: date) -> dict:
    """
    Aggregates raw outlet readings for one device/day.
    Returns a dict ready for upsert into daily_summaries.

    Only processes sensor_type='outlet' readings — inlet readings are
    excluded because they are not stored for analytics (inlet handles
    leak detection locally on the ESP32).
    """
    async with AsyncSessionLocal() as db:

        # ── Fetch MQTT string slugs for denormalised columns ──────────────
        network_id_slug, zone_id_slug = await _get_device_slugs(device_id, db)

        # ── Aggregate outlet readings for this device/day ─────────────────
        result = await db.execute(
            select(
                func.avg(Reading.flow_rate).label("avg_flow"),
                func.max(Reading.flow_rate).label("max_flow"),
                func.min(Reading.flow_rate).label("min_flow"),
                func.max(Reading.total_volume).label("vol_end"),
                func.min(Reading.total_volume).label("vol_start"),
                func.count().label("count"),
            )
            .where(
                Reading.device_id   == device_id,
                Reading.sensor_type == "outlet",       # only outlet readings
                func.date(Reading.timestamp) == target_date,
            )
        )
        row = result.one()

        # ── Count leak events for this device/day ─────────────────────────
        leak_result = await db.execute(
            select(func.count()).where(
                Event.device_id  == device_id,
                Event.event_type == "leak_detected",
                func.date(Event.timestamp) == target_date,
            )
        )
        leak_count = leak_result.scalar() or 0

        # ── Volume = odometer end - odometer start ────────────────────────
        # Uses max/min of total_volume (cumulative counter) for the day.
        # max(0) guards against sensor resets mid-day producing a negative.
        volume = float((row.vol_end or 0) - (row.vol_start or 0))

        return dict(
            device_id           = device_id,
            network_id          = network_id_slug,   # MQTT string slug
            zone_id             = zone_id_slug,      # MQTT string slug
            sensor_type         = "outlet",
            summary_date        = target_date,
            total_volume_litres = max(volume, 0),
            avg_flow_rate       = float(row.avg_flow or 0),
            max_flow_rate       = float(row.max_flow or 0),
            min_flow_rate       = float(row.min_flow or 0),
            reading_count       = int(row.count or 0),
            leak_event_count    = leak_count,
        )


async def run_daily_aggregation(target_date: date = None) -> None:
    """
    Run aggregation for ALL active devices for a given date.
    Called nightly at 00:05 UTC for the previous day.
    Skips devices with zero readings (e.g. offline that day).
    """
    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    logger.info("Running daily aggregation for %s", target_date)

    # Fetch all active device IDs in one query
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Device.device_id).where(Device.status == "active")
        )
        device_ids = [row[0] for row in result.all()]

    logger.info("Aggregating %d active devices for %s", len(device_ids), target_date)

    for device_id in device_ids:
        try:
            summary = await compute_daily_summary(device_id, target_date)

            # Skip devices with no readings that day — don't write empty rows
            if summary["reading_count"] == 0:
                logger.debug("No readings for device=%s on %s — skipping", device_id, target_date)
                continue

            async with AsyncSessionLocal() as db:
                stmt = pg_insert(DailySummary).values(**summary)
                stmt = stmt.on_conflict_do_update(
                    # uq_daily_summary is now (device_id, summary_date, sensor_type)
                    constraint="uq_daily_summary",
                    set_={
                        "network_id":          stmt.excluded.network_id,
                        "zone_id":             stmt.excluded.zone_id,
                        "total_volume_litres": stmt.excluded.total_volume_litres,
                        "avg_flow_rate":       stmt.excluded.avg_flow_rate,
                        "max_flow_rate":       stmt.excluded.max_flow_rate,
                        "min_flow_rate":       stmt.excluded.min_flow_rate,
                        "reading_count":       stmt.excluded.reading_count,
                        "leak_event_count":    stmt.excluded.leak_event_count,
                        "updated_at":          func.now(),
                    }
                )
                await db.execute(stmt)
                await db.commit()
                logger.info(
                    "Summary saved: device=%s network=%s zone=%s date=%s readings=%d vol=%.2fL",
                    device_id,
                    summary["network_id"],
                    summary["zone_id"],
                    target_date,
                    summary["reading_count"],
                    summary["total_volume_litres"],
                )

        except Exception as exc:
            logger.error("Aggregation failed for device=%s date=%s: %s", device_id, target_date, exc)


async def schedule_aggregation() -> None:
    """
    Infinite loop that fires run_daily_aggregation() every night at 00:05 UTC.
    Started as an asyncio background task from main.py lifespan.
    """
    while True:
        now      = datetime.now(timezone.utc)
        next_run = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        logger.info(
            "Next aggregation in %.0f seconds (at %s UTC)",
            wait_seconds,
            next_run.strftime("%Y-%m-%d %H:%M"),
        )
        await asyncio.sleep(wait_seconds)
        await run_daily_aggregation()