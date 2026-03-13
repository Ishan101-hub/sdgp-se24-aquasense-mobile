# analytics_router.py
# AquaSense v3 — Analytics Router
#
# All endpoints read from daily_summaries (pre-aggregated).
# Raw readings are only touched for the live graph endpoint.
#
# Endpoints:
#   GET /analytics/{device_id}/live              — last N raw readings (live chart)
#   GET /analytics/{device_id}/usage/daily       — daily breakdown for one month
#   GET /analytics/{device_id}/usage/monthly     — monthly rollup for one year
#   GET /analytics/{device_id}/leaks             — leak event history
#   GET /analytics/zone/{zone_id}/summary        — NEW: zone-level monthly aggregation
#   GET /analytics/network/{network_id}/summary  — network-level monthly aggregation
#
# Ownership chain enforced on every endpoint:
#   current_user → Network.owner_id → Zone.network_id → Device.zone_id

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract

from database import get_db
from auth import get_current_user
from models import User, Network, Zone, Device, Reading, DailySummary, Event

router = APIRouter(prefix="/analytics", tags=["analytics"])

_current_year  = datetime.now(timezone.utc).year
_current_month = datetime.now(timezone.utc).month


# ─────────────────────────────────────────────────────────────────────────────
#  Shared ownership helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _resolve_device(device_id: str, user: User, db: AsyncSession) -> Device:
    """
    Fetch device and verify ownership chain:
      current_user → Network → Zone → Device
    Raises 404 if device is not found or does not belong to the user.
    """
    result = await db.execute(
        select(Device)
        .join(Zone,    Device.zone_id    == Zone.id)
        .join(Network, Zone.network_id   == Network.id)
        .where(
            Device.device_id   == device_id,
            Network.owner_id   == user.id,
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


async def _resolve_zone(zone_id: str, user: User, db: AsyncSession) -> Zone:
    """Fetch zone and verify it belongs to one of the user's networks."""
    result = await db.execute(
        select(Zone)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.zone_id == zone_id, Network.owner_id == user.id)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


async def _resolve_network(network_id: int, user: User, db: AsyncSession) -> Network:
    """Fetch network and verify ownership."""
    result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == user.id)
    )
    net = result.scalar_one_or_none()
    if not net:
        raise HTTPException(status_code=404, detail="Network not found")
    return net


# ─────────────────────────────────────────────────────────────────────────────
#  1. LIVE GRAPH — last N raw readings
#     Flutter home dashboard chart polling every 2s
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/live")
async def live_readings(
    device_id: str,
    limit: int = Query(default=120, le=600),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Returns the most recent N outlet readings for a real-time chart.
    Hits the ix_readings_outlet_partial index — only scans outlet rows.
    """
    await _resolve_device(device_id, current_user, db)

    result = await db.execute(
        select(Reading)
        .where(
            Reading.device_id   == device_id,
            Reading.sensor_type == "outlet",     # partial index hit
        )
        .order_by(Reading.timestamp.desc())
        .limit(limit)
    )
    readings = result.scalars().all()

    return {
        "device_id": device_id,
        "count":     len(readings),
        "readings": [
            {
                "flow_rate":    float(r.flow_rate),
                "total_volume": float(r.total_volume),
                "valve_status": r.valve_status,
                "timestamp":    r.timestamp.isoformat(),
            }
            for r in reversed(readings)   # oldest-first for charting
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  2. DAILY BREAKDOWN — one month from daily_summaries
#     Home screen chart + Report screen daily tab
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/usage/daily")
async def daily_usage(
    device_id:    str,
    year:         int = Query(default=_current_year),
    month:        int = Query(default=_current_month, ge=1, le=12),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Daily water usage for one calendar month.
    Reads from daily_summaries — never scans raw readings.
    Filters sensor_type='outlet' to exclude inlet sensor rows.
    """
    await _resolve_device(device_id, current_user, db)

    result = await db.execute(
        select(DailySummary)
        .where(
            DailySummary.device_id   == device_id,
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
        .order_by(DailySummary.summary_date)
    )
    rows = result.scalars().all()

    return {
        "device_id": device_id,
        "year":      year,
        "month":     month,
        "count":     len(rows),
        "daily": [
            {
                "date":                r.summary_date.isoformat(),
                "total_volume_litres": float(r.total_volume_litres or 0),
                "avg_flow_rate":       float(r.avg_flow_rate or 0),
                "max_flow_rate":       float(r.max_flow_rate or 0),
                "reading_count":       r.reading_count,
                "leak_events":         r.leak_event_count,
            }
            for r in rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  3. MONTHLY ROLLUP — full year from daily_summaries
#     Report screen Monthly chart
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/usage/monthly")
async def monthly_usage(
    device_id:    str,
    year:         int = Query(default=_current_year),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    12-month rollup for a device.
    O(365) rows max from daily_summaries — no raw reading scan.
    sensor_type='outlet' filter ensures only outlet data is included.
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
            DailySummary.device_id   == device_id,
            DailySummary.sensor_type == "outlet",
            extract("year", DailySummary.summary_date) == year,
        )
        .group_by("month")
        .order_by("month")
    )

    return {
        "device_id": device_id,
        "year":      year,
        "monthly": [
            {
                "month":               int(row.month),
                "total_volume_litres": float(row.total_volume or 0),
                "avg_flow_rate":       round(float(row.avg_flow  or 0), 4),
                "max_flow_rate":       round(float(row.max_flow  or 0), 4),
                "reading_count":       int(row.readings or 0),
                "leak_events":         int(row.leaks    or 0),
            }
            for row in result
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  4. LEAK HISTORY — Event table, filtered to leak_detected
#     Leakages screen + Alerts screen
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/leaks")
async def leak_history(
    device_id:    str,
    resolved:     Optional[bool] = Query(default=None),
    limit:        int            = Query(default=50, le=200),
    db:           AsyncSession   = Depends(get_db),
    current_user: User           = Depends(get_current_user),
):
    """
    Leak event history for a device.
    resolved=None  → all leaks
    resolved=false → open leaks (notification bell, Leakages screen badge)
    resolved=true  → resolved leaks (history)
    Uses ix_events_unresolved_leaks partial index for resolved=false queries.
    """
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
        "count":     len(events),
        "leaks": [
            {
                "id":          e.id,
                "severity":    e.severity,
                "description": e.description,
                "resolved":    e.resolved,
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
                "timestamp":   e.timestamp.isoformat(),
            }
            for e in events
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  5. ZONE SUMMARY — NEW
#     Aggregates all outlet devices in a zone for a given month.
#     Uses ix_daily_network_zone_date index.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zone/{zone_id}/summary")
async def zone_summary(
    zone_id:      str,
    year:         int = Query(default=_current_year),
    month:        int = Query(default=_current_month, ge=1, le=12),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    ZONE-LEVEL MONTHLY SUMMARY
    Aggregates all outlet devices in the zone for the given year/month.

    Response powers the Leakages screen zone card:
      zone_total_volume_litres   — total water used in the zone this month
      zone_total_leaks           — total leak events in the zone
      devices[]                  — per-device breakdown

    Ownership: current_user → Network → Zone verified.
    Uses the ix_daily_network_zone_date composite index.
    """
    zone = await _resolve_zone(zone_id, current_user, db)

    # Get all devices in this zone
    dev_result = await db.execute(
        select(Device)
        .where(Device.zone_id == zone.id, Device.status == "active")
    )
    devices = dev_result.scalars().all()
    if not devices:
        return {
            "zone_id":                  zone_id,
            "zone_name":                zone.zone_name,
            "year":                     year,
            "month":                    month,
            "zone_total_volume_litres": 0.0,
            "zone_total_leaks":         0,
            "devices":                  [],
        }

    # Single aggregation query over daily_summaries for all zone devices
    # Uses ix_daily_network_zone_date: network_id, zone_id, summary_date
    result = await db.execute(
        select(
            DailySummary.device_id,
            func.sum(DailySummary.total_volume_litres).label("total_volume"),
            func.sum(DailySummary.leak_event_count).label("total_leaks"),
            func.sum(DailySummary.reading_count).label("total_readings"),
            func.avg(DailySummary.avg_flow_rate).label("avg_flow"),
        )
        .where(
            DailySummary.zone_id     == zone_id,      # denormalised string slug
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
        .group_by(DailySummary.device_id)
        .order_by(DailySummary.device_id)
    )
    rows = result.all()

    # Build device name lookup from ORM objects
    name_map = {d.device_id: d.subline_name for d in devices}

    zone_total_volume = sum(float(r.total_volume or 0) for r in rows)
    zone_total_leaks  = sum(int(r.total_leaks   or 0) for r in rows)

    return {
        "zone_id":                  zone_id,
        "zone_name":                zone.zone_name,
        "year":                     year,
        "month":                    month,
        "zone_total_volume_litres": round(zone_total_volume, 2),
        "zone_total_leaks":         zone_total_leaks,
        "devices": [
            {
                "device_id":           r.device_id,
                "subline_name":        name_map.get(r.device_id),
                "total_volume_litres": round(float(r.total_volume or 0), 2),
                "total_leaks":         int(r.total_leaks   or 0),
                "total_readings":      int(r.total_readings or 0),
                "avg_flow_rate":       round(float(r.avg_flow     or 0), 4),
            }
            for r in rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  6. NETWORK SUMMARY — aggregated per zone then per device
#     Report screen — Monthly Water Usage top card
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/network/{network_id}/summary")
async def network_summary(
    network_id:   int,
    year:         int = Query(default=_current_year),
    month:        int = Query(default=_current_month, ge=1, le=12),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    NETWORK-LEVEL MONTHLY SUMMARY
    Groups devices by zone, then aggregates each zone's daily_summaries.

    Response shape:
      network_total_volume_litres
      zones[]:
        zone_id
        zone_name
        zone_total_volume_litres
        devices[]: { device_id, subline_name, total_volume_litres, total_leaks }

    Ownership: current_user → Network verified.
    All analytics from daily_summaries — no raw reading scan.
    """
    network = await _resolve_network(network_id, current_user, db)

    # One query: daily_summaries → devices → zones, grouped by zone + device
    result = await db.execute(
        select(
            DailySummary.zone_id.label("z_id"),
            DailySummary.device_id,
            func.sum(DailySummary.total_volume_litres).label("total_volume"),
            func.sum(DailySummary.leak_event_count).label("total_leaks"),
            func.sum(DailySummary.reading_count).label("total_readings"),
        )
        .join(Device,  DailySummary.device_id == Device.device_id)
        .join(Zone,    Device.zone_id          == Zone.id)
        .where(
            Zone.network_id              == network_id,
            DailySummary.sensor_type     == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
        .group_by(DailySummary.zone_id, DailySummary.device_id)
        .order_by(DailySummary.zone_id, DailySummary.device_id)
    )
    rows = result.all()

    # Fetch zone name lookup
    zone_result = await db.execute(
        select(Zone).where(Zone.network_id == network_id)
    )
    zone_map = {z.zone_id: z.zone_name for z in zone_result.scalars()}

    # Fetch device subline_name lookup
    dev_result = await db.execute(
        select(Device)
        .join(Zone,    Device.zone_id    == Zone.id)
        .where(Zone.network_id == network_id)
    )
    dev_map = {d.device_id: d.subline_name for d in dev_result.scalars()}

    # Group rows by zone
    zones_dict: dict[str, dict] = {}
    for row in rows:
        zid = row.z_id
        if zid not in zones_dict:
            zones_dict[zid] = {
                "zone_id":                  zid,
                "zone_name":                zone_map.get(zid),
                "zone_total_volume_litres": 0.0,
                "zone_total_leaks":         0,
                "devices":                  [],
            }
        vol = float(row.total_volume or 0)
        zones_dict[zid]["zone_total_volume_litres"] += vol
        zones_dict[zid]["zone_total_leaks"]         += int(row.total_leaks or 0)
        zones_dict[zid]["devices"].append({
            "device_id":           row.device_id,
            "subline_name":        dev_map.get(row.device_id),
            "total_volume_litres": round(vol, 2),
            "total_leaks":         int(row.total_leaks    or 0),
            "total_readings":      int(row.total_readings or 0),
        })

    zones_list = list(zones_dict.values())
    for z in zones_list:
        z["zone_total_volume_litres"] = round(z["zone_total_volume_litres"], 2)

    network_total = sum(z["zone_total_volume_litres"] for z in zones_list)

    return {
        "network_id":                   network_id,
        "network_name":                 network.name,
        "year":                         year,
        "month":                        month,
        "network_total_volume_litres":  round(network_total, 2),
        "zones":                        zones_list,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  7. ZONE LEAK HISTORY — leak events across all devices in a zone
#     Leakage screen zone-level alerts
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zone/{zone_id}/leaks")
async def zone_leak_history(
    zone_id:      int,
    resolved:     Optional[bool] = Query(default=None),
    limit:        int            = Query(default=50, le=200),
    db:           AsyncSession   = Depends(get_db),
    current_user: User           = Depends(get_current_user),
):
    """
    Leak and flow_mismatch event history for all devices in a zone.
    Ownership: current_user → Network → Zone verified.

    resolved=None  → all events
    resolved=false → open (unresolved) events only
    resolved=true  → resolved events only
    """
    # Ownership check
    zone_result = await db.execute(
        select(Zone)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.id == zone_id, Network.owner_id == current_user.id)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    # Get all device IDs in this zone
    dev_result = await db.execute(
        select(Device.device_id).where(Device.zone_id == zone_id)
    )
    device_ids = [row[0] for row in dev_result.all()]

    if not device_ids:
        return {"zone_id": zone_id, "zone": zone.zone_name, "count": 0, "leaks": []}

    query = (
        select(Event)
        .where(
            Event.device_id.in_(device_ids),
            Event.event_type.in_(["leak_detected", "flow_mismatch"]),
        )
        .order_by(Event.timestamp.desc())
        .limit(limit)
    )
    if resolved is not None:
        query = query.where(Event.resolved == resolved)

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "zone_id": zone_id,
        "zone":    zone.zone_name,
        "count":   len(events),
        "leaks": [
            {
                "id":          e.id,
                "device_id":   e.device_id,
                "event_type":  e.event_type,
                "severity":    e.severity,
                "description": e.description,
                "resolved":    e.resolved,
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
                "timestamp":   e.timestamp.isoformat(),
            }
            for e in events
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  8. DASHBOARD TODAY — today's water usage stats
#     Flutter dashboard TodayCard: litresUsed, dailyAverage, percent
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/today")
async def dashboard_today(
    network_id:   Optional[int] = Query(default=None, description="Filter to a specific network"),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(get_current_user),
):
    """
    Today's water usage across all the user's devices (or a single network).

    Returns:
      litresUsed    — total volume consumed today (from raw readings)
      dailyAverage  — 30-day rolling average from daily_summaries
      percent       — litresUsed / dailyAverage * 100 (capped at 200 for display)
      active_leaks  — count of unresolved leak/flow_mismatch events today
    """
    today = datetime.now(timezone.utc).date()

    # Resolve the user's network IDs (or a single one)
    if network_id is not None:
        net_result = await db.execute(
            select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
        )
        if not net_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Network not found")
        network_ids = [network_id]
    else:
        net_result = await db.execute(
            select(Network.id).where(Network.owner_id == current_user.id)
        )
        network_ids = [row[0] for row in net_result.all()]

    if not network_ids:
        return {"litresUsed": 0.0, "dailyAverage": 0.0, "percent": 0.0, "active_leaks": 0}

    # Collect all outlet device IDs belonging to these networks
    dev_result = await db.execute(
        select(Device.device_id)
        .where(
            Device.network_id.in_(network_ids),
            Device.sensor_type == "outlet",
            Device.status == "active",
        )
    )
    device_ids = [row[0] for row in dev_result.all()]

    if not device_ids:
        return {"litresUsed": 0.0, "dailyAverage": 0.0, "percent": 0.0, "active_leaks": 0}

    # ── Today's volume: max(total_volume) - min(total_volume) per device ──────
    # Mirrors the aggregation logic in aggregation.py
    today_result = await db.execute(
        select(
            func.sum(func.coalesce(Reading.total_volume, 0)).label("vol_sum"),
        )
        .where(
            Reading.device_id.in_(device_ids),
            Reading.sensor_type == "outlet",
            func.date(Reading.timestamp) == today,
        )
    )
    # Use max-min odometer approach per device for accuracy
    today_vol_result = await db.execute(
        select(
            Reading.device_id,
            func.max(Reading.total_volume).label("vol_end"),
            func.min(Reading.total_volume).label("vol_start"),
        )
        .where(
            Reading.device_id.in_(device_ids),
            Reading.sensor_type == "outlet",
            func.date(Reading.timestamp) == today,
        )
        .group_by(Reading.device_id)
    )
    litres_used = sum(
        max(float((r.vol_end or 0) - (r.vol_start or 0)), 0.0)
        for r in today_vol_result.all()
    )

    # ── 30-day average from daily_summaries ───────────────────────────────────
    thirty_days_ago = today - timedelta(days=30)
    avg_result = await db.execute(
        select(func.avg(DailySummary.total_volume_litres).label("daily_avg"))
        .where(
            DailySummary.device_id.in_(device_ids),
            DailySummary.sensor_type == "outlet",
            DailySummary.summary_date >= thirty_days_ago,
            DailySummary.summary_date < today,
            DailySummary.reading_count > 0,
        )
    )
    daily_avg = float(avg_result.scalar() or 0.0)

    percent = round((litres_used / daily_avg * 100) if daily_avg > 0 else 0.0, 1)
    percent = min(percent, 200.0)   # cap for display safety

    # ── Active (unresolved) leaks today ───────────────────────────────────────
    leak_count_result = await db.execute(
        select(func.count()).where(
            Event.device_id.in_(device_ids),
            Event.event_type.in_(["leak_detected", "flow_mismatch"]),
            Event.resolved == False,
            func.date(Event.timestamp) == today,
        )
    )
    active_leaks = int(leak_count_result.scalar() or 0)

    return {
        "date":         today.isoformat(),
        "litresUsed":   round(litres_used, 2),
        "dailyAverage": round(daily_avg, 2),
        "percent":      percent,
        "active_leaks": active_leaks,
    }