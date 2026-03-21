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
#
# Auth: every endpoint requires Bearer JWT token from POST /auth/login
# The Flutter app sends:  Authorization: Bearer <token>

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
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
    """
    Returns the user's first network, or the specified network if network_id given.
    Raises 404 if user has no networks or specified network not found.
    """
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
    """How many days have passed in the given month (including today)."""
    today = date.today()
    if today.year == year and today.month == month:
        return today.day
    return monthrange(year, month)[1]


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/zones/daily
#
#  Called by: HomePage._fetchData()  →  DailyConsumptionCard + TodayCard
#
#  Returns a list of zones with today's usage and 30-day average.
#  Flutter maps this directly to WaterZone objects:
#    _zones = zonesData.map((z) => WaterZone(
#        name:    z['name'],
#        used:    z['used'],
#        average: z['average'],
#    )).toList();
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
      {"name": "Bathroom 02", "used": 80.0,  "average": 100.0},
      {"name": "Kitchen 01",  "used": 80.0,  "average": 100.0},
      {"name": "Outdoor 01",  "used": 50.0,  "average": 80.0}
    ]

    "used"    = litres consumed today (max - min of total_volume)
    "average" = 30-day rolling daily average from daily_summaries
    """
    network = await _get_user_network(current_user, db, network_id)
    today   = date.today()

    # ── All zones in this network ordered for consistent card layout ──────
    zone_result = await db.execute(
        select(Zone)
        .where(Zone.network_id == network.id)
        .order_by(Zone.zone_type, Zone.zone_id)
    )
    zones = zone_result.scalars().all()
    if not zones:
        return []

    zone_id_strings = [z.zone_id for z in zones]

    # ── Today's usage per zone (odometer: max - min of total_volume) ──────
    # Groups by zone_id (denormalised string slug in readings table)
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

    # ── 30-day daily average per zone from daily_summaries ────────────────
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

    # ── Build response in exact shape Flutter expects ─────────────────────
    return [
        {
            "name":    zone.zone_name,                          # e.g. "Bathroom 01"
            "used":    round(today_by_zone.get(zone.zone_id, 0.0), 2),
            "average": round(avg_by_zone.get(zone.zone_id, 0.0), 2),
            # Extra fields Flutter can optionally use:
            "zone_id":   zone.zone_id,
            "zone_type": zone.zone_type,
            "floor":     zone.floor,
        }
        for zone in zones
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/flowrate
#
#  Called by: HomePage._fetchData()  →  WaterStatusCard
#
#  Returns the most recent outlet flow rate across all the user's devices.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/flowrate")
async def live_flowrate(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Live flow rate for the WaterStatusCard water drop.

    Response shape:
    {"flow_rate": 23.1, "valve_state": "open", "unit": "L/min",
     "device_id": "esp32_k1", "timestamp": "2026-03-13T10:30:00+00:00"}
    """
    network = await _get_user_network(current_user, db, network_id)

    # Most recent outlet reading across all network devices
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
#  Powers the TodayCard circular arc gauge and percentage text.
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

    # Today's volume (odometer method per device, summed)
    today_vol = await db.execute(
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
        for r in today_vol.all()
    )

    # 30-day rolling average
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
            Event.event_type.in_(["leak_detected", "flow_mismatch"]),
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
#  Powers the Leakages screen — one card per zone with IN/OUT + valve toggle.
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
        "ui_state":    "leak_detected"   ← "leak_detected"|"valve_closed"|"normal"
      },
      ...
    ]
    """
    network = await _get_user_network(current_user, db, network_id)

    zone_result = await db.execute(
        select(Zone)
        .where(Zone.network_id == network.id)
        .order_by(Zone.zone_type, Zone.zone_id)
    )
    zones = zone_result.scalars().all()

    response = []
    for zone in zones:
        # Latest inlet reading for this zone
        inlet_result = await db.execute(
            select(Reading.flow_rate)
            .join(Device, Reading.device_id == Device.device_id)
            .where(
                Device.zone_id      == zone.id,
                Reading.sensor_type == "inlet",
            )
            .order_by(Reading.timestamp.desc())
            .limit(1)
        )
        # Latest outlet reading + valve state for this zone
        outlet_result = await db.execute(
            select(Reading.flow_rate, Device.valve_state)
            .join(Device, Reading.device_id == Device.device_id)
            .where(
                Device.zone_id      == zone.id,
                Reading.sensor_type == "outlet",
            )
            .order_by(Reading.timestamp.desc())
            .limit(1)
        )

        inlet_row   = inlet_result.one_or_none()
        outlet_row  = outlet_result.one_or_none()
        in_flow     = float(inlet_row.flow_rate)  if inlet_row  else 0.0
        out_flow    = float(outlet_row.flow_rate) if outlet_row else 0.0
        valve_state = outlet_row.valve_state      if outlet_row else "unknown"
        leak        = (in_flow - out_flow) >= 0.1 and valve_state == "open"

        # UI colour state — matches Flutter card border colour logic
        if leak:
            ui_state = "leak_detected"   # red
        elif valve_state == "closed":
            ui_state = "valve_closed"    # amber/gold
        else:
            ui_state = "normal"          # blue/green

        response.append({
            "zone_id":     zone.id,         # integer PK for valve command
            "zone_slug":   zone.zone_id,    # MQTT slug
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
#
#  Leakages screen valve toggle. Always shows confirm dialog before calling.
# ─────────────────────────────────────────────────────────────────────────────

class ValveCommandBody(BaseModel):
    zone_id:  int    # Zone.id (integer PK from /mobile/leakages response)
    action:   str    # "open" | "close"
    override: bool = False  # True = force open even during active leak


@router.post("/valve")
async def mobile_valve_command(
    body:         ValveCommandBody,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    """
    Send open/close command to all outlet devices in a zone.
    Flutter should show a confirmation dialog before calling this.
    """
    if body.action not in ("open", "close"):
        raise HTTPException(status_code=400, detail="action must be 'open' or 'close'")

    # Ownership check
    zone_result = await db.execute(
        select(Zone)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.id == body.zone_id, Network.owner_id == current_user.id)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    # Check for active leak — block open unless override=True
    if body.action == "open" and not body.override:
        leak_check = await db.execute(
            select(func.count()).where(
                Event.zone_id    == body.zone_id,
                Event.event_type.in_(["leak_detected", "flow_mismatch"]),
                Event.resolved   == False,
            )
        )
        if (leak_check.scalar() or 0) > 0:
            raise HTTPException(
                status_code=409,
                detail="Active leak detected. Resolve the alert first, "
                       "then send with override=true."
            )

    # Load network slug for MQTT topic
    net_result = await db.execute(
        select(Network).where(Network.id == zone.network_id)
    )
    network = net_result.scalar_one()

    # Find all outlet devices in this zone
    dev_result = await db.execute(
        select(Device)
        .where(
            Device.zone_id     == body.zone_id,
            Device.sensor_type == "outlet",
            Device.status      == "active",
        )
    )
    devices = dev_result.scalars().all()
    if not devices:
        raise HTTPException(status_code=404, detail="No active outlet devices in zone")

    sent = []
    for device in devices:
        # Update DB valve state
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
            severity    = "low",
            description = f"Valve manually {body.action}d via mobile app "
                          f"by user {current_user.id}.",
        ))
        # Publish MQTT command
        if _publish_queue:
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
#
#  Report screen — monthly summary with year/month selector.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/report/monthly")
async def monthly_report(
    year:         int           = Query(default=datetime.now(timezone.utc).year),
    month:        int           = Query(default=datetime.now(timezone.utc).month, ge=1, le=12),
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Monthly report for the Report screen year/month dropdown.

    Response shape:
    {
      "year": 2026, "month": 3,
      "total_usage_L":  15250.0,
      "weekly_avg_L":   3812.5,
      "daily_avg_L":    508.3,
      "leaks_detected": 3,
      "days_with_data": 13
    }
    """
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
#
#  Notification bell badge count + alert list screen.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def mobile_alerts(
    resolved:     bool          = Query(default=False),
    network_id:   Optional[int] = Query(default=None),
    limit:        int           = Query(default=50, le=200),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Leak alert list for the notification bell screen.

    resolved=false (default) → open alerts → use count as bell badge number
    resolved=true            → past resolved alerts

    Response shape:
    {
      "unread_count": 2,
      "items": [
        {
          "id": 1,
          "zone_name": "Kitchen 01",
          "event_type": "leak_detected",
          "severity": "high",
          "description": "...",
          "resolved": false,
          "timestamp": "2026-03-13T10:00:00+00:00"
        }
      ]
    }
    """
    network    = await _get_user_network(current_user, db, network_id)
    device_ids = await _get_outlet_device_ids(network.id, db)

    if not device_ids:
        return {"unread_count": 0, "items": []}

    # Zone name lookup for display
    zone_result = await db.execute(
        select(Zone).where(Zone.network_id == network.id)
    )
    zone_map = {z.id: z.zone_name for z in zone_result.scalars()}

    dev_zone_result = await db.execute(
        select(Device.device_id, Device.zone_id)
        .where(Device.device_id.in_(device_ids))
    )
    dev_zone_map = {row.device_id: row.zone_id for row in dev_zone_result.all()}

    # Unread count (always count unresolved regardless of resolved filter)
    unread_result = await db.execute(
        select(func.count()).where(
            Event.device_id.in_(device_ids),
            Event.event_type.in_(["leak_detected", "flow_mismatch"]),
            Event.resolved == False,
        )
    )
    unread_count = int(unread_result.scalar() or 0)

    # Alert list
    query = (
        select(Event)
        .where(
            Event.device_id.in_(device_ids),
            Event.event_type.in_(["leak_detected", "flow_mismatch"]),
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
#  POST /mobile/alerts/{alert_id}/resolve
#
#  Mark an alert as resolved before sending valve open command.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id:     int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    """
    Resolve a leak alert. Call this before POST /mobile/valve with action=open.
    Ownership verified: event → device → network → current_user.
    """
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

    return {
        "status":      "resolved",
        "alert_id":    alert_id,
        "resolved_at": event.resolved_at.isoformat(),
    }