

# mobile_router.py
# AquaSense v3.1 — Mobile API Router
#
# All endpoints the Flutter app calls directly.
# Designed to match the exact JSON shapes the Flutter code expects.
#
# Endpoints:
#   GET /mobile/zones/daily        → DailyConsumptionCard + TodayCard zones list
#   GET /mobile/flowrate           → WaterStatusCard live flow rate
#   GET /mobile/dashboard/today    → TodayCard totals (litresUsed, percent, dailyAverage)
#   GET /mobile/leakages           → Leakages screen per-zone IN/OUT + valve state
#   POST /mobile/valve             → Leakages screen valve toggle
#   GET /mobile/report/monthly     → Report screen monthly summary
#   GET /mobile/alerts             → Notification bell alert list + unread count
#   POST /mobile/alerts/{id}/resolve → Resolve a leak alert
#   GET /mobile/notifications — leak push notifications (polled every 15s)
#
# Auth: every endpoint requires Bearer JWT token from POST /auth/login
# The Flutter app sends:  Authorization: Bearer <token>
#
# Fix (v3.1.1):
#   • leakages() — replaced N*2 per-zone DB queries with 3 bulk queries +
#     Python-side processing. Same fix as network_zones_flow_status in
#     device_router.py.
#   • leakages() and dashboard_today() — leak threshold now reads from
#     leak_service.FLOW_MISMATCH_THRESHOLD_LPM instead of hardcoded 0.1.
#   • dashboard_today() — today's volume now uses restart-safe consecutive-
#     delta odometer instead of max-min (which breaks on ESP32 restart).

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from itertools import groupby
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from auth import get_current_user as _iot_dep
from database import get_db
from models import (
    User, Network, Zone, Device,
    Reading, DailySummary, Event, ValveLog,
)
from leak_service import FLOW_MISMATCH_THRESHOLD_LPM   # ← FIX: shared threshold constant

router = APIRouter(prefix="/mobile", tags=["mobile"])

# ─── Shared publish queue (injected by main.py) ───────────────────────────────
_publish_queue = None

def set_mobile_publish_queue(q) -> None:
    global _publish_queue
    _publish_queue = q


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_user_network(
    user: User,
    db: AsyncSession,
    network_id: Optional[int] = None,
) -> Network:
    query = select(Network).where(Network.owner_id == user.id)
    if network_id:
        query = query.where(Network.id == network_id)
    result = await db.execute(query.limit(1))
    net = result.scalar_one_or_none()
    if not net:
        raise HTTPException(
            status_code=404,
            detail="No network found. Register a network first."
        )
    return net


async def _get_outlet_device_ids(network_id: int, db: AsyncSession) -> list[str]:
    """All active outlet device IDs for a network."""
    result = await db.execute(
        select(Device.device_id)
        .where(
            Device.network_id  == network_id,
            Device.sensor_type == "outlet",
            Device.status      == "active",
        )
    )
    return [row[0] for row in result.all()]


def _days_elapsed_in_month(year: int, month: int) -> int:
    today = date.today()
    if today.year == year and today.month == month:
        return today.day
    return monthrange(year, month)[1]


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/zones/daily
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zones/daily")
async def zones_daily(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Per-zone daily usage for the Flutter DailyConsumptionCard.

    Response shape (list — one item per zone instance):
    [
      {"name": "Bathroom 01", "used": 60.0,  "average": 100.0},
      ...
    ]
    """
    network = await _get_user_network(current_user, db, network_id)
    today   = date.today()

    zone_result = await db.execute(
        select(Zone)
        .where(Zone.network_id == network.id)
        .order_by(Zone.zone_type, Zone.zone_id)
    )
    zones = zone_result.scalars().all()
    if not zones:
        return []

    zone_id_strings = [z.zone_id for z in zones]

    today_result = await db.execute(
        select(
            Reading.zone_id,
            func.max(Reading.total_volume).label("vol_end"),
            func.min(Reading.total_volume).label("vol_start"),
        )
        .join(Device, Reading.device_id == Device.device_id)
        .where(
            Device.network_id       == network.id,
            Reading.sensor_type     == "outlet",
            Reading.zone_id.in_(zone_id_strings),
            func.date(Reading.timestamp) == today,
        )
        .group_by(Reading.zone_id)
    )
    today_by_zone = {
        row.zone_id: max(float((row.vol_end or 0) - (row.vol_start or 0)), 0.0)
        for row in today_result.all()
    }

    thirty_days_ago = today - timedelta(days=30)
    avg_result = await db.execute(
        select(
            DailySummary.zone_id,
            func.avg(DailySummary.total_volume_litres).label("daily_avg"),
        )
        .where(
            DailySummary.zone_id.in_(zone_id_strings),
            DailySummary.sensor_type == "outlet",
            DailySummary.summary_date >= thirty_days_ago,
            DailySummary.summary_date < today,
            DailySummary.reading_count > 0,
        )
        .group_by(DailySummary.zone_id)
    )
    avg_by_zone = {
        row.zone_id: float(row.daily_avg or 0)
        for row in avg_result.all()
    }

    return [
        {
            "name":      zone.zone_name,
            "used":      round(today_by_zone.get(zone.zone_id, 0.0), 2),
            "average":   round(avg_by_zone.get(zone.zone_id, 0.0), 2),
            "zone_id":   zone.zone_id,
            "zone_type": zone.zone_type,
            "floor":     zone.floor,
        }
        for zone in zones
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/flowrate
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/flowrate")
async def live_flowrate(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """Live flow rate for the WaterStatusCard water drop."""
    network = await _get_user_network(current_user, db, network_id)

    result = await db.execute(
        select(Reading.flow_rate, Reading.device_id, Reading.timestamp,
               Device.valve_state)
        .join(Device, Reading.device_id == Device.device_id)
        .where(
            Device.network_id      == network.id,
            Device.sensor_type     == "outlet",
            Device.status          == "active",
            Reading.sensor_type    == "outlet",
        )
        .order_by(Reading.timestamp.desc())
        .limit(1)
    )
    row = result.one_or_none()

    if row is None:
        return {
            "flow_rate":   0.0,
            "valve_state": "unknown",
            "unit":        "L/min",
            "device_id":   None,
            "timestamp":   None,
        }

    return {
        "flow_rate":   round(float(row.flow_rate), 2),
        "valve_state": row.valve_state,
        "unit":        "L/min",
        "device_id":   row.device_id,
        "timestamp":   row.timestamp.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/dashboard/today
#
#  FIX (v3.1.1): today's volume now uses restart-safe consecutive-delta
#  odometer. See analytics_router.py dashboard_today() for full explanation.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/today")
async def dashboard_today(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Today's total usage for the TodayCard.

    Response shape:
    {
      "litresUsed":   220.0,
      "dailyAverage": 460.0,
      "percent":      47.8,
      "active_leaks": 1,
      "date":         "2026-03-13"
    }
    """
    network    = await _get_user_network(current_user, db, network_id)
    device_ids = await _get_outlet_device_ids(network.id, db)
    today      = date.today()

    if not device_ids:
        return {
            "litresUsed": 0.0, "dailyAverage": 0.0,
            "percent": 0.0, "active_leaks": 0,
            "date": today.isoformat(),
        }

    # Step 1: try today's daily_summaries first (if aggregation ran today)
    summary_result = await db.execute(
        select(func.sum(DailySummary.total_volume_litres).label("total"))
        .where(
            DailySummary.device_id.in_(device_ids),
            DailySummary.sensor_type == "outlet",
            DailySummary.summary_date == today,
            DailySummary.reading_count > 0,
        )
    )
    summary_total = summary_result.scalar()

    if summary_total is not None:
        litres_used = float(summary_total)
    else:
        # Step 2: restart-safe consecutive-delta odometer from raw readings
        raw_result = await db.execute(
            select(Reading.device_id, Reading.total_volume, Reading.timestamp)
            .where(
                Reading.device_id.in_(device_ids),
                Reading.sensor_type == "outlet",
                func.date(Reading.timestamp) == today,
            )
            .order_by(Reading.device_id, Reading.timestamp.asc())
        )
        raw_rows = raw_result.all()

        litres_used = 0.0
        for _device_id, readings in groupby(raw_rows, key=lambda r: r.device_id):
            readings_list = list(readings)
            for i in range(1, len(readings_list)):
                delta = float(readings_list[i].total_volume) - float(readings_list[i - 1].total_volume)
                if delta > 0:   # skip negative deltas caused by device restart
                    litres_used += delta

    # Step 3: 30-day historical daily average (excludes today + empty days)
    thirty_days_ago = today - timedelta(days=30)
    avg_result = await db.execute(
        select(func.avg(DailySummary.total_volume_litres))
        .where(
            DailySummary.device_id.in_(device_ids),
            DailySummary.sensor_type == "outlet",
            DailySummary.summary_date >= thirty_days_ago,
            DailySummary.summary_date < today,
            DailySummary.reading_count > 0,
        )
    )
    daily_avg = float(avg_result.scalar() or 0.0)
    percent   = round((litres_used / daily_avg * 100) if daily_avg > 0 else 0.0, 1)
    percent   = min(percent, 200.0)

    # Unresolved leaks today
    leak_result = await db.execute(
        select(func.count()).where(
            Event.device_id.in_(device_ids),
            Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
            Event.resolved == False,
            func.date(Event.timestamp) == today,
        )
    )
    active_leaks = int(leak_result.scalar() or 0)

    return {
        "litresUsed":   round(litres_used, 2),
        "dailyAverage": round(daily_avg, 2),
        "percent":      percent,
        "active_leaks": active_leaks,
        "date":         today.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/leakages
#
#  FIX (v3.1.1): replaced N*2 per-zone DB queries with 3 bulk queries.
#  Previous implementation ran 2 queries per zone inside a for-loop.
#  New approach is identical to the fix in device_router.network_zones_flow_status.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/leakages")
async def leakages(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    All zones with live IN/OUT flow and valve state for the Leakages screen.

    Response shape (list — one item per zone):
    [
      {
        "zone_id":     "kitchen_01",
        "zone_name":   "Kitchen 01",
        "zone_type":   "kitchen",
        "floor":       "ground",
        "inFlow":      23.1,
        "outFlow":     15.7,
        "valve_state": "open",
        "leak":        true,
        "ui_state":    "leak_detected"
      },
      ...
    ]
    """
    network = await _get_user_network(current_user, db, network_id)

    # ── Query 1: all zones ────────────────────────────────────────────────
    zone_result = await db.execute(
        select(Zone)
        .where(Zone.network_id == network.id)
        .order_by(Zone.zone_type, Zone.zone_id)
    )
    zones = zone_result.scalars().all()
    if not zones:
        return []

    zone_ids = [z.id for z in zones]

    # ── Query 2: latest inlet reading per zone ────────────────────────────
    inlet_sub = (
        select(
            Device.zone_id,
            func.max(Reading.timestamp).label("latest_ts"),
        )
        .join(Reading, Reading.device_id == Device.device_id)
        .where(
            Device.zone_id.in_(zone_ids),
            Reading.sensor_type == "inlet",
        )
        .group_by(Device.zone_id)
        .subquery()
    )
    inlet_result = await db.execute(
        select(Device.zone_id, Reading.flow_rate)
        .join(Reading, Reading.device_id == Device.device_id)
        .join(
            inlet_sub,
            (inlet_sub.c.zone_id   == Device.zone_id) &
            (inlet_sub.c.latest_ts == Reading.timestamp),
        )
        .where(Reading.sensor_type == "inlet")
    )
    inlet_by_zone: dict[int, float] = {}
    for row in inlet_result.all():
        if row.zone_id not in inlet_by_zone:
            inlet_by_zone[row.zone_id] = float(row.flow_rate)

    # ── Query 3: latest outlet reading + valve state per zone ─────────────
    outlet_sub = (
        select(
            Device.zone_id,
            func.max(Reading.timestamp).label("latest_ts"),
        )
        .join(Reading, Reading.device_id == Device.device_id)
        .where(
            Device.zone_id.in_(zone_ids),
            Reading.sensor_type == "outlet",
        )
        .group_by(Device.zone_id)
        .subquery()
    )
    outlet_result = await db.execute(
        select(Device.zone_id, Reading.flow_rate, Device.valve_state)
        .join(Reading, Reading.device_id == Device.device_id)
        .join(
            outlet_sub,
            (outlet_sub.c.zone_id   == Device.zone_id) &
            (outlet_sub.c.latest_ts == Reading.timestamp),
        )
        .where(Reading.sensor_type == "outlet")
    )
    outlet_by_zone: dict[int, dict] = {}
    for row in outlet_result.all():
        if row.zone_id not in outlet_by_zone:
            outlet_by_zone[row.zone_id] = {
                "flow_rate":   float(row.flow_rate),
                "valve_state": row.valve_state,
            }

    # ── Build response in Python ──────────────────────────────────────────
    response = []
    for zone in zones:
        in_flow     = inlet_by_zone.get(zone.id, 0.0)
        outlet_data = outlet_by_zone.get(zone.id, {})
        out_flow    = outlet_data.get("flow_rate",   0.0)
        valve_state = outlet_data.get("valve_state", "unknown")

        # FIX: use shared threshold constant — was hardcoded 0.1
        leak = (in_flow - out_flow) >= FLOW_MISMATCH_THRESHOLD_LPM and valve_state == "open"

        if leak:
            ui_state = "leak_detected"
        elif valve_state == "closed":
            ui_state = "valve_closed"
        else:
            ui_state = "normal"

        response.append({
            "zone_id":     zone.id,
            "zone_slug":   zone.zone_id,
            "zone_name":   zone.zone_name,
            "zone_type":   zone.zone_type,
            "floor":       zone.floor,
            "inFlow":      round(in_flow,  2),
            "outFlow":     round(out_flow, 2),
            "valve_state": valve_state,
            "leak":        leak,
            "ui_state":    ui_state,
        })

    return response


# ─────────────────────────────────────────────────────────────────────────────
#  POST /mobile/valve
# ─────────────────────────────────────────────────────────────────────────────

class ValveCommandBody(BaseModel):
    zone_id:  int
    action:   str
    override: bool = False


@router.post("/valve")
async def mobile_valve_command(
    body:         ValveCommandBody,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    """Send open/close command to all outlet devices in a zone."""
    if body.action not in ("open", "close"):
        raise HTTPException(status_code=400, detail="action must be 'open' or 'close'")

    zone_result = await db.execute(
        select(Zone)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.id == body.zone_id, Network.owner_id == current_user.id)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    if body.action == "open" and not body.override:
        leak_check = await db.execute(
            select(func.count()).where(
                Event.zone_id    == body.zone_id,
                Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
                Event.resolved   == False,
            )
        )
        if (leak_check.scalar() or 0) > 0:
            raise HTTPException(
                status_code=409,
                detail="Active leak detected. Resolve the alert first, "
                       "then send with override=true."
            )

    net_result = await db.execute(
        select(Network).where(Network.id == zone.network_id)
    )
    network = net_result.scalar_one()

    # ── Query INLET devices — the valve relay is wired to the inlet ESP32 ──
    # The inlet ESP32 (pipe_01) has the relay and subscribes to valve/command.
    # The outlet ESP32 only measures flow — it has no valve control.
    # Publishing to the outlet device's MQTT topic would be silently ignored
    # by the inlet ESP32 because it only subscribes to its own topic.
    inlet_result = await db.execute(
        select(Device)
        .where(
            Device.zone_id     == body.zone_id,
            Device.sensor_type == "inlet",
            Device.status      == "active",
        )
    )
    inlet_devices = inlet_result.scalars().all()
    if not inlet_devices:
        raise HTTPException(status_code=404, detail="No active inlet devices in zone")

    sent = []
    for device in inlet_devices:
        device.valve_state = body.action
        db.add(ValveLog(
            device_id    = device.device_id,
            commanded_by = current_user.id,
            action       = body.action,
            source       = "manual",
        ))
        db.add(Event(
            device_id   = device.device_id,
            network_id  = device.network_id,
            zone_id     = device.zone_id,
            event_type  = f"valve_{body.action}d",
            description = f"Valve manually {body.action}d via mobile app "
                          f"by user {current_user.id}.",
        ))
        if _publish_queue:
            # MQTT topic → aquasense/{network}/{zone}/{inlet_device_id}/valve/command
            # The inlet ESP32 subscribes to exactly this topic.
            await _publish_queue.put(
                (network.network_id, zone.zone_id, device.device_id, body.action)
            )
        sent.append(device.device_id)

    await db.commit()

    return {
        "status":     "commands_sent",
        "zone_id":    body.zone_id,
        "zone_name":  zone.zone_name,
        "action":     body.action,
        "devices":    sent,
        "count":      len(sent),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/report/monthly
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/report/monthly")
async def monthly_report(
    year:         int           = Query(default=datetime.now(timezone.utc).year),
    month:        int           = Query(default=datetime.now(timezone.utc).month, ge=1, le=12),
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """Monthly report for the Report screen year/month dropdown."""
    network    = await _get_user_network(current_user, db, network_id)
    device_ids = await _get_outlet_device_ids(network.id, db)

    if not device_ids:
        return {
            "year": year, "month": month,
            "total_usage_L": 0.0, "weekly_avg_L": 0.0,
            "daily_avg_L": 0.0, "leaks_detected": 0, "days_with_data": 0,
        }

    result = await db.execute(
        select(
            func.sum(DailySummary.total_volume_litres).label("total"),
            func.count(DailySummary.id).label("days"),
            func.sum(DailySummary.leak_event_count).label("leaks"),
        )
        .where(
            DailySummary.device_id.in_(device_ids),
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
            DailySummary.reading_count > 0,
        )
    )
    row        = result.one()
    total      = float(row.total or 0)
    days       = int(row.days   or 0) or 1
    leaks      = int(row.leaks  or 0)
    daily_avg  = total / days
    weekly_avg = total / max(days / 7, 1)

    return {
        "year":          year,
        "month":         month,
        "total_usage_L": round(total,      2),
        "weekly_avg_L":  round(weekly_avg, 2),
        "daily_avg_L":   round(daily_avg,  2),
        "leaks_detected": leaks,
        "days_with_data": days,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/alerts
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def mobile_alerts(
    resolved:     bool          = Query(default=False),
    network_id:   Optional[int] = Query(default=None),
    limit:        int           = Query(default=50, le=200),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """Leak alert list for the notification bell screen."""
    network    = await _get_user_network(current_user, db, network_id)
    device_ids = await _get_outlet_device_ids(network.id, db)

    if not device_ids:
        return {"unread_count": 0, "items": []}

    zone_result = await db.execute(
        select(Zone).where(Zone.network_id == network.id)
    )
    zone_map = {z.id: z.zone_name for z in zone_result.scalars()}

    dev_zone_result = await db.execute(
        select(Device.device_id, Device.zone_id)
        .where(Device.device_id.in_(device_ids))
    )
    dev_zone_map = {row.device_id: row.zone_id for row in dev_zone_result.all()}

    unread_result = await db.execute(
        select(func.count()).where(
            Event.device_id.in_(device_ids),
            Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
            Event.resolved == False,
        )
    )
    unread_count = int(unread_result.scalar() or 0)

    query = (
        select(Event)
        .where(
            Event.device_id.in_(device_ids),
            Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
            Event.resolved == resolved,
        )
        .order_by(Event.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "unread_count": unread_count,
        "items": [
            {
                "id":          e.id,
                "zone_name":   zone_map.get(dev_zone_map.get(e.device_id), "Unknown Zone"),
                "device_id":   e.device_id,
                "event_type":  e.event_type,
                "description": e.description,
                "resolved":    e.resolved,
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
                "timestamp":   e.timestamp.isoformat(),
            }
            for e in events
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  POST /mobile/alerts/{alert_id}/resolve
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id:     int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    """Resolve a leak alert. Call this before POST /mobile/valve with action=open."""
    result = await db.execute(
        select(Event)
        .join(Device,  Event.device_id   == Device.device_id)
        .join(Network, Device.network_id == Network.id)
        .where(Event.id == alert_id, Network.owner_id == current_user.id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Alert not found")
    if event.resolved:
        return {"status": "already_resolved", "alert_id": alert_id}

    event.resolved    = True
    event.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    # Clear in-memory leak state so counter resets for this zone
    from leak_service import get_leak_service
    svc = get_leak_service()
    if svc and event.zone_id:
        await svc.clear_leak(event.zone_id)
        if event.event_type == "valve_failure":
            await svc.clear_valve_failure(event.zone_id)

    return {
        "status":      "resolved",
        "alert_id":    alert_id,
        "resolved_at": event.resolved_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/notifications
#
#  Bell button notification list — only leak events where the valve was
#  auto-closed. Scoped to the current user's network via ownership check.
#  Auth required — same as every other endpoint in this router.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Returns notifications for leak events where the valve was auto-closed.
    Flutter BellButton calls this every 15 seconds.

    Response shape (list):
    [
      {
        "title":            "Leak Detected: Kitchen 01",
        "message":          "Leak detected in Kitchen 01 pipeline. Valve auto-closed.",
        "type":             "leak",
        "time":             "5 mins ago",
        "target_tab_index": 1
      }
    ]
    """
    # Ownership check — consistent with all other mobile endpoints
    network = await _get_user_network(current_user, db, network_id)
    device_ids = await _get_outlet_device_ids(network.id, db)

    if not device_ids:
        return []

    # Zone name lookup
    zone_result = await db.execute(
        select(Zone).where(Zone.network_id == network.id)
    )
    zone_map = {z.id: z.zone_name for z in zone_result.scalars()}

    dev_zone_result = await db.execute(
        select(Device.device_id, Device.zone_id)
        .where(Device.device_id.in_(device_ids))
    )
    dev_zone_map = {row.device_id: row.zone_id for row in dev_zone_result.all()}

    # Unresolved leak events for this user's devices
    events_result = await db.execute(
        select(Event)
        .where(
            Event.device_id.in_(device_ids),
            Event.event_type == "leak_detected",
            Event.resolved   == False,
        )
        .order_by(Event.timestamp.desc())
        .limit(20)
    )
    events = events_result.scalars().all()

    now           = datetime.now(timezone.utc)
    notifications = []

    for event in events:
        # Only notify if this device had an auto_leak valve close —
        # i.e. the valve was actually closed automatically, not just a logged event
        valve_result = await db.execute(
            select(ValveLog)
            .where(
                ValveLog.device_id == event.device_id,
                ValveLog.source    == "auto_leak",
                ValveLog.action    == "close",
            )
            .order_by(ValveLog.commanded_at.desc())
            .limit(1)
        )
        if valve_result.scalar_one_or_none() is None:
            continue   # no auto-close found — skip

        # Human-readable relative time
        diff = (now - event.timestamp).total_seconds()
        if diff < 60:
            time_str = "Just now"
        elif diff < 3600:
            time_str = f"{int(diff / 60)} mins ago"
        elif diff < 86400:
            time_str = f"{int(diff / 3600)} hrs ago"
        else:
            time_str = f"{int(diff / 86400)} days ago"

        zone_name = zone_map.get(dev_zone_map.get(event.device_id), "Unknown Zone")

        notifications.append({
            "title":            f"Leak Detected: {zone_name}",
            "message":          (
                f"Leak detected in {zone_name} pipeline. "
                f"Valve has been automatically closed. "
                f"Please check the pipeline immediately."
            ),
            "type":             "leak",
            "time":             time_str,
            "target_tab_index": 1,   # → Leakages tab in Flutter
        })

    return notifications