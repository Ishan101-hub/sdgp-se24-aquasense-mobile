# app/routers/analytics_router.py
# AquaSense v2 – Analytics: live graph, monthly usage, leak history, network-level aggregation

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, text

from database import get_db
from auth import get_current_user
from models import User, Network, Device, Reading, DailySummary, Event

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _resolve_device(device_id: str, user: User, db: AsyncSession) -> Device:
    """Verify the device belongs to a network owned by this user."""
    result = await db.execute(
        select(Device)
        .join(Network, Device.network_id == Network.id)
        .where(Device.device_id == device_id, Network.owner_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# ── 1. Live graph – last N readings for a device ─────────────────────────────
@router.get("/{device_id}/live")
async def live_readings(
    device_id: str,
    limit: int = Query(default=120, le=600, description="Number of recent readings"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the most recent readings for a real-time device graph.
    Uses the composite index (device_id, timestamp DESC) for sub-millisecond
    partition pruning on the readings table.
    """
    await _resolve_device(device_id, current_user, db)

    result = await db.execute(
        select(Reading)
        .where(Reading.device_id == device_id)
        .order_by(Reading.timestamp.desc())
        .limit(limit)
    )
    readings = result.scalars().all()
    return {
        "device_id": device_id,
        "readings": [
            {
                "flow_rate": float(r.flow_rate),
                "total_volume": float(r.total_volume),
                "valve_status": r.valve_status,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in reversed(readings)   # return oldest-first for charting
        ],
    }


# ── 2. Monthly usage – from daily_summaries (pre-aggregated) ─────────────────
@router.get("/{device_id}/usage/monthly")
async def monthly_usage(
    device_id: str,
    year: int = Query(default=datetime.now(timezone.utc).year),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Monthly water consumption from pre-aggregated daily_summaries.
    Never scans raw readings — O(30) rows instead of O(2.5M).
    """
    await _resolve_device(device_id, current_user, db)

    result = await db.execute(
        select(
            extract("month", DailySummary.summary_date).label("month"),
            func.sum(DailySummary.total_volume_litres).label("total_volume"),
            func.avg(DailySummary.avg_flow_rate).label("avg_flow"),
            func.max(DailySummary.max_flow_rate).label("max_flow"),
            func.sum(DailySummary.reading_count).label("readings"),
            func.sum(DailySummary.leak_event_count).label("leaks"),
        )
        .where(
            DailySummary.device_id == device_id,
            extract("year", DailySummary.summary_date) == year,
        )
        .group_by("month")
        .order_by("month")
    )

    return {
        "device_id": device_id,
        "year": year,
        "monthly": [
            {
                "month": int(row.month),
                "total_volume_litres": float(row.total_volume or 0),
                "avg_flow_rate": round(float(row.avg_flow or 0), 4),
                "max_flow_rate": round(float(row.max_flow or 0), 4),
                "reading_count": int(row.readings or 0),
                "leak_events": int(row.leaks or 0),
            }
            for row in result
        ],
    }


# ── 3. Daily usage breakdown for one month ───────────────────────────────────
@router.get("/{device_id}/usage/daily")
async def daily_usage(
    device_id: str,
    year: int = Query(default=datetime.now(timezone.utc).year),
    month: int = Query(default=datetime.now(timezone.utc).month),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _resolve_device(device_id, current_user, db)

    result = await db.execute(
        select(DailySummary)
        .where(
            DailySummary.device_id == device_id,
            extract("year", DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
        .order_by(DailySummary.summary_date)
    )
    rows = result.scalars().all()
    return {
        "device_id": device_id,
        "year": year,
        "month": month,
        "daily": [
            {
                "date": r.summary_date.isoformat(),
                "total_volume_litres": float(r.total_volume_litres or 0),
                "avg_flow_rate": float(r.avg_flow_rate or 0),
                "max_flow_rate": float(r.max_flow_rate or 0),
                "reading_count": r.reading_count,
                "leak_events": r.leak_event_count,
            }
            for r in rows
        ],
    }


# ── 4. Leak history ──────────────────────────────────────────────────────────
@router.get("/{device_id}/leaks")
async def leak_history(
    device_id: str,
    resolved: bool = Query(default=None, description="Filter by resolved status"),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _resolve_device(device_id, current_user, db)

    query = (
        select(Event)
        .where(Event.device_id == device_id, Event.event_type == "leak_detected")
        .order_by(Event.timestamp.desc())
        .limit(limit)
    )
    if resolved is not None:
        query = query.where(Event.resolved == resolved)

    result = await db.execute(query)
    events = result.scalars().all()
    return {
        "device_id": device_id,
        "leaks": [
            {
                "id": e.id,
                "severity": e.severity,
                "description": e.description,
                "resolved": e.resolved,
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ],
    }


# ── 5. Network-level aggregation ─────────────────────────────────────────────
@router.get("/network/{network_id}/summary")
async def network_summary(
    network_id: int,
    year: int = Query(default=datetime.now(timezone.utc).year),
    month: int = Query(default=datetime.now(timezone.utc).month),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregates all devices in a network for a given month.
    Joins daily_summaries → devices → networks in one query.
    """
    # Verify ownership
    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    result = await db.execute(
        select(
            Device.device_id,
            Device.subline_name,
            func.sum(DailySummary.total_volume_litres).label("total_volume"),
            func.sum(DailySummary.leak_event_count).label("total_leaks"),
            func.sum(DailySummary.reading_count).label("total_readings"),
        )
        .join(DailySummary, DailySummary.device_id == Device.device_id)
        .where(
            Device.network_id == network_id,
            extract("year", DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
        .group_by(Device.device_id, Device.subline_name)
        .order_by(Device.device_id)
    )

    rows = result.all()
    total_volume = sum(float(r.total_volume or 0) for r in rows)
    return {
        "network_id": network_id,
        "year": year,
        "month": month,
        "network_total_volume_litres": total_volume,
        "devices": [
            {
                "device_id": r.device_id,
                "subline_name": r.subline_name,
                "total_volume_litres": float(r.total_volume or 0),
                "total_leaks": int(r.total_leaks or 0),
                "total_readings": int(r.total_readings or 0),
            }
            for r in rows
        ],
    }
