# app/aggregation.py
# AquaSense v2 – Daily summary aggregation
# Run as a background task (every midnight) or triggered via APScheduler

import logging
from datetime import date, timedelta

from sqlalchemy import select, func, extract, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models import Device, Reading, DailySummary, Event

logger = logging.getLogger("aquasense.aggregation")


async def compute_daily_summary(device_id: str, target_date: date) -> dict:
    """
    Aggregates raw readings for one device/day.
    Returns dict ready for upsert into daily_summaries.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                func.sum(Reading.flow_rate).label("sum_flow"),
                func.avg(Reading.flow_rate).label("avg_flow"),
                func.max(Reading.flow_rate).label("max_flow"),
                func.min(Reading.flow_rate).label("min_flow"),
                func.max(Reading.total_volume).label("vol_end"),
                func.min(Reading.total_volume).label("vol_start"),
                func.count().label("count"),
            )
            .where(
                Reading.device_id == device_id,
                func.date(Reading.timestamp) == target_date,
            )
        )
        row = result.one()

        # Count leak events for the day
        leak_result = await db.execute(
            select(func.count()).where(
                Event.device_id == device_id,
                Event.event_type == "leak_detected",
                func.date(Event.timestamp) == target_date,
            )
        )
        leak_count = leak_result.scalar() or 0

        # Volume consumed = end total_volume - start total_volume (odometer style)
        volume = float((row.vol_end or 0) - (row.vol_start or 0))

        return dict(
            device_id=device_id,
            summary_date=target_date,
            total_volume_litres=max(volume, 0),
            avg_flow_rate=float(row.avg_flow or 0),
            max_flow_rate=float(row.max_flow or 0),
            min_flow_rate=float(row.min_flow or 0),
            reading_count=int(row.count or 0),
            leak_event_count=leak_count,
        )


async def run_daily_aggregation(target_date: date = None) -> None:
    """
    Run aggregation for all active devices for a given date.
    Called nightly (e.g. 00:05 UTC) for previous day.
    """
    if target_date is None:
        from datetime import datetime, timezone
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    logger.info("Running daily aggregation for %s", target_date)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Device.device_id).where(Device.status == "active")
        )
        device_ids = [row[0] for row in result.all()]

    for device_id in device_ids:
        try:
            summary = await compute_daily_summary(device_id, target_date)
            if summary["reading_count"] == 0:
                continue  # no data for this device today

            async with AsyncSessionLocal() as db:
                stmt = pg_insert(DailySummary).values(**summary)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_daily_summary",
                    set_={
                        "total_volume_litres": stmt.excluded.total_volume_litres,
                        "avg_flow_rate":       stmt.excluded.avg_flow_rate,
                        "max_flow_rate":       stmt.excluded.max_flow_rate,
                        "min_flow_rate":       stmt.excluded.min_flow_rate,
                        "reading_count":       stmt.excluded.reading_count,
                        "leak_event_count":    stmt.excluded.leak_event_count,
                    }
                )
                await db.execute(stmt)
                await db.commit()
                logger.info("Summary saved: device=%s date=%s readings=%d",
                            device_id, target_date, summary["reading_count"])
        except Exception as exc:
            logger.error("Aggregation failed for device=%s: %s", device_id, exc)


async def schedule_aggregation() -> None:
    """
    Runs nightly at 00:05 UTC in the background.
    Start this with asyncio.create_task() from main.py lifespan.
    """
    import asyncio
    from datetime import datetime, timezone

    while True:
        now = datetime.now(timezone.utc)
        # Calculate seconds until next 00:05 UTC
        next_run = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info("Next aggregation scheduled in %.0f seconds", wait_seconds)
        await asyncio.sleep(wait_seconds)
        await run_daily_aggregation()
