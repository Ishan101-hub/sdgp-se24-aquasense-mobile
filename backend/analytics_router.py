# analytics_router.py
# AquaSense v3.1 — Analytics Router
#
# Changes from v3:
#   • all_zones_summary — new GET /analytics/zones/summary endpoint
#   • zone_summary      — adds zone_type and floor to response
#   • network_summary   — adds zone_type and floor per zone group
#   • _get_network_slug removed — network slug now passed directly via zones[0].network.network_id
#     using a joined load instead of accessing a lazy relationship
#   • zone_type filter supported on all_zones_summary (?zone_type=bathroom)

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, case
from sqlalchemy.orm import joinedload

from database import get_db
from auth import get_current_user as _iot_dep
from models import User, Network, Zone, Device, Reading, DailySummary, Event

router = APIRouter(prefix="/analytics", tags=["analytics"])

_current_year  = datetime.now(timezone.utc).year
_current_month = datetime.now(timezone.utc).month


# ─────────────────────────────────────────────────────────────────────────────
#  Ownership helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _resolve_device(device_id: str, user: User, db: AsyncSession) -> Device:
    result = await db.execute(
        select(Device)
        .join(Zone,    Device.zone_id    == Zone.id)
        .join(Network, Zone.network_id   == Network.id)
        .where(Device.device_id == device_id, Network.owner_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


async def _resolve_zone(zone_id: str, user: User, db: AsyncSession) -> Zone:
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
    result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == user.id)
    )
    net = result.scalar_one_or_none()
    if not net:
        raise HTTPException(status_code=404, detail="Network not found")
    return net


def _usage_status(total: float, avg: float) -> str:
    if avg == 0:
        return "no_data"
    ratio = total / avg
    if ratio > 1.2:
        return "over_limit"
    if ratio < 0.5:
        return "low"
    return "normal"


# ─────────────────────────────────────────────────────────────────────────────
#  1. LIVE READINGS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/live")
async def live_readings(
    device_id:    str,
    limit:        int          = Query(default=120, le=600),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    await _resolve_device(device_id, current_user, db)

    result = await db.execute(
        select(Reading)
        .where(Reading.device_id == device_id, Reading.sensor_type == "outlet")
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
            for r in reversed(readings)
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  2. DAILY BREAKDOWN
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/usage/daily")
async def daily_usage(
    device_id:    str,
    year:         int          = Query(default=_current_year),
    month:        int          = Query(default=_current_month, ge=1, le=12),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
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
        "year": year, "month": month, "count": len(rows),
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
#  3. MONTHLY ROLLUP
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/usage/monthly")
async def monthly_usage(
    device_id:    str,
    year:         int          = Query(default=_current_year),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
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
        "device_id": device_id, "year": year,
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
#  4. LEAK HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{device_id}/leaks")
async def leak_history(
    device_id:    str,
    resolved:     Optional[bool] = Query(default=None),
    limit:        int             = Query(default=50, le=200),
    db:           AsyncSession    = Depends(get_db),
    current_user: User            = Depends(_iot_dep),
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
        "device_id": device_id, "count": len(events),
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
#  5. ALL ZONES SUMMARY  ← primary Flutter dashboard endpoint
#
#  GET /analytics/zones/summary?network_id=1&year=2026&month=3
#  GET /analytics/zones/summary?network_id=1&zone_type=bathroom
#
#  Returns one entry per zone INSTANCE.
#  bathroom_01 and bathroom_02 are always separate rows — never merged.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zones/summary")
async def all_zones_summary(
    network_id:   int,
    year:         int           = Query(default=_current_year),
    month:        int           = Query(default=_current_month, ge=1, le=12),
    zone_type:    Optional[str] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Returns one usage card per zone instance for the Flutter dashboard.
    Flutter iterates this list — no hardcoded zone names needed.

    Fields per entry:
      zone_id, zone_name, zone_type, floor   — identity
      daily_usage_L, monthly_total_L,
      daily_avg_L, status                    — usage
      leak_events                            — alerts
      valve_state                            — open|closed|mixed
    """
    network = await _resolve_network(network_id, current_user, db)

    # ── Fetch zones, eagerly joining Network to get network_id slug ───────
    zone_query = (
        select(Zone)
        .options(joinedload(Zone.network))
        .where(Zone.network_id == network_id)
    )
    if zone_type:
        zone_query = zone_query.where(Zone.zone_type == zone_type)
    zone_query = zone_query.order_by(Zone.zone_type, Zone.zone_id)

    zone_result = await db.execute(zone_query)
    zones = zone_result.scalars().unique().all()

    if not zones:
        return []

    zone_id_strings = [z.zone_id for z in zones]
    network_slug    = network.network_id   # string slug from the loaded Network object

    # ── Monthly totals per zone ───────────────────────────────────────────
    monthly_result = await db.execute(
        select(
            DailySummary.zone_id,
            func.sum(DailySummary.total_volume_litres).label("monthly_total"),
            func.sum(DailySummary.leak_event_count).label("leak_events"),
        )
        .where(
            DailySummary.network_id  == network_slug,
            DailySummary.zone_id.in_(zone_id_strings),
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
        .group_by(DailySummary.zone_id)
    )
    monthly_by_zone = {
        row.zone_id: {"monthly_total": float(row.monthly_total or 0),
                      "leak_events":   int(row.leak_events    or 0)}
        for row in monthly_result
    }

    # ── 30-day historical daily average per zone ──────────────────────────
    avg_result = await db.execute(
        select(
            DailySummary.zone_id,
            func.avg(DailySummary.total_volume_litres).label("daily_avg"),
        )
        .where(
            DailySummary.zone_id.in_(zone_id_strings),
            DailySummary.sensor_type == "outlet",
        )
        .group_by(DailySummary.zone_id)
    )
    avg_by_zone = {row.zone_id: float(row.daily_avg or 0) for row in avg_result}

    # ── Current valve state per zone ──────────────────────────────────────
    valve_result = await db.execute(
        select(
            Zone.zone_id,
            func.count(Device.id).label("total"),
            func.sum(case((Device.valve_state == "open", 1), else_=0)).label("open_count"),
        )
        .join(Device, Device.zone_id == Zone.id)
        .where(
            Zone.network_id    == network_id,
            Zone.zone_id.in_(zone_id_strings),
            Device.sensor_type == "outlet",
            Device.status      == "active",
        )
        .group_by(Zone.zone_id)
    )
    valve_by_zone: dict[str, str] = {}
    for row in valve_result:
        if row.open_count == 0:
            valve_by_zone[row.zone_id] = "closed"
        elif row.open_count == row.total:
            valve_by_zone[row.zone_id] = "open"
        else:
            valve_by_zone[row.zone_id] = "mixed"

    # ── Build response ────────────────────────────────────────────────────
    days_in_month = monthrange(year, month)[1]
    today         = date.today()

    response = []
    for zone in zones:
        zid          = zone.zone_id
        m_data       = monthly_by_zone.get(zid, {"monthly_total": 0, "leak_events": 0})
        monthly_total = m_data["monthly_total"]
        daily_avg    = avg_by_zone.get(zid, 0)

        days_elapsed = today.day if (today.year == year and today.month == month) else days_in_month
        today_usage  = monthly_total / max(days_elapsed, 1)

        response.append({
            "zone_id":         zid,
            "zone_name":       zone.zone_name,
            "zone_type":       zone.zone_type,
            "floor":           zone.floor,
            "daily_usage_L":   round(today_usage,    2),
            "monthly_total_L": round(monthly_total,  2),
            "daily_avg_L":     round(daily_avg,       2),
            "status":          _usage_status(today_usage, daily_avg),
            "leak_events":     m_data["leak_events"],
            "valve_state":     valve_by_zone.get(zid, "unknown"),
        })

    return response


# ─────────────────────────────────────────────────────────────────────────────
#  6. SINGLE ZONE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zone/{zone_id}/summary")
async def zone_summary(
    zone_id:      str,
    year:         int          = Query(default=_current_year),
    month:        int          = Query(default=_current_month, ge=1, le=12),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    zone = await _resolve_zone(zone_id, current_user, db)

    result = await db.execute(
        select(
            func.sum(DailySummary.total_volume_litres).label("total_volume"),
            func.sum(DailySummary.leak_event_count).label("total_leaks"),
            func.avg(DailySummary.avg_flow_rate).label("avg_flow"),
        )
        .where(
            DailySummary.zone_id     == zone_id,
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
    )
    row = result.one_or_none()

    dev_result = await db.execute(
        select(
            DailySummary.device_id,
            func.sum(DailySummary.total_volume_litres).label("total_volume"),
            func.sum(DailySummary.leak_event_count).label("total_leaks"),
        )
        .where(
            DailySummary.zone_id     == zone_id,
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
        )
        .group_by(DailySummary.device_id)
    )
    dev_rows = dev_result.all()

    devices_result = await db.execute(
        select(Device).where(Device.zone_id == zone.id, Device.status == "active")
    )
    name_map = {d.device_id: d.subline_name for d in devices_result.scalars()}

    return {
        "zone_id":                  zone_id,
        "zone_name":                zone.zone_name,
        "zone_type":                zone.zone_type,
        "floor":                    zone.floor,
        "year":                     year,
        "month":                    month,
        "zone_total_volume_litres": round(float(row.total_volume or 0), 2) if row else 0.0,
        "zone_total_leaks":         int(row.total_leaks or 0)              if row else 0,
        "avg_flow_rate":            round(float(row.avg_flow or 0), 4)     if row else 0.0,
        "devices": [
            {
                "device_id":           r.device_id,
                "subline_name":        name_map.get(r.device_id),
                "total_volume_litres": round(float(r.total_volume or 0), 2),
                "total_leaks":         int(r.total_leaks or 0),
            }
            for r in dev_rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  7. NETWORK SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/network/{network_id}/summary")
async def network_summary(
    network_id:   int,
    year:         int          = Query(default=_current_year),
    month:        int          = Query(default=_current_month, ge=1, le=12),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    network = await _resolve_network(network_id, current_user, db)

    result = await db.execute(
        select(
            DailySummary.zone_id.label("z_id"),
            DailySummary.device_id,
            func.sum(DailySummary.total_volume_litres).label("total_volume"),
            func.sum(DailySummary.leak_event_count).label("total_leaks"),
            func.sum(DailySummary.reading_count).label("total_readings"),
        )
        .join(Device, DailySummary.device_id == Device.device_id)
        .join(Zone,   Device.zone_id          == Zone.id)
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

    zone_result = await db.execute(select(Zone).where(Zone.network_id == network_id))
    zone_map = {z.zone_id: z for z in zone_result.scalars()}

    dev_result = await db.execute(
        select(Device)
        .join(Zone, Device.zone_id == Zone.id)
        .where(Zone.network_id == network_id)
    )
    dev_map = {d.device_id: d.subline_name for d in dev_result.scalars()}

    zones_dict: dict[str, dict] = {}
    for row in rows:
        zid = row.z_id
        if zid not in zones_dict:
            z = zone_map.get(zid)
            zones_dict[zid] = {
                "zone_id":                  zid,
                "zone_name":                z.zone_name  if z else zid,
                "zone_type":                z.zone_type  if z else "unknown",   # ← NEW
                "floor":                    z.floor      if z else None,         # ← NEW
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

    return {
        "network_id":                  network_id,
        "network_name":                network.name,
        "year":                        year,
        "month":                       month,
        "network_total_volume_litres": round(sum(z["zone_total_volume_litres"] for z in zones_list), 2),
        "zones":                       zones_list,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  8. ZONE LEAK HISTORY  (kept from v3 — unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zone/{zone_id}/leaks")
async def zone_leak_history(
    zone_id:      int,
    resolved:     Optional[bool] = Query(default=None),
    limit:        int            = Query(default=50, le=200),
    db:           AsyncSession   = Depends(get_db),
    current_user: User           = Depends(_iot_dep),
):
    zone_result = await db.execute(
        select(Zone)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.id == zone_id, Network.owner_id == current_user.id)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

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
        "zone_id": zone_id, "zone": zone.zone_name, "count": len(events),
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
#  9. DASHBOARD TODAY  (kept from v3 — unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/today")
async def dashboard_today(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    today = datetime.now(timezone.utc).date()

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
    daily_avg   = float(avg_result.scalar() or 0.0)
    percent     = round((litres_used / daily_avg * 100) if daily_avg > 0 else 0.0, 1)
    percent     = min(percent, 200.0)

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