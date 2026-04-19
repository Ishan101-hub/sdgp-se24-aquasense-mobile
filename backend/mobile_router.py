

# # # mobile_router.py
# # # AquaSense v3.1 — Mobile API Router
# # #
# # # All endpoints the Flutter app calls directly.
# # # Designed to match the exact JSON shapes the Flutter code expects.
# # #
# # # Endpoints:
# # #   GET /mobile/zones/daily        → DailyConsumptionCard + TodayCard zones list
# # #   GET /mobile/flowrate           → WaterStatusCard live flow rate
# # #   GET /mobile/dashboard/today    → TodayCard totals (litresUsed, percent, dailyAverage)
# # #   GET /mobile/leakages           → Leakages screen per-zone IN/OUT + valve state
# # #   POST /mobile/valve             → Leakages screen valve toggle
# # #   GET /mobile/report/monthly     → Report screen monthly summary
# # #   GET /mobile/alerts             → Notification bell alert list + unread count
# # #   POST /mobile/alerts/{id}/resolve → Resolve a leak alert
# # #   GET /mobile/notifications — leak push notifications (polled every 15s)
# # #
# # # Auth: every endpoint requires Bearer JWT token from POST /auth/login
# # # The Flutter app sends:  Authorization: Bearer <token>
# # #

# #
# # Changes v3.3:
# #
# # FIX A — Leakages outlet/inlet flow not showing (GET /mobile/leakages):
# #   The inlet and outlet outer queries were missing Device.sensor_type and
# #   Device.status filters.  Without them the zone_id join could silently
# #   match the wrong device (inlet matched where outlet expected or vice-
# #   versa), causing the timestamp equality condition to find no rows and
# #   returning 0.0 for one or both flow values.
# #   Both outer queries now explicitly filter:
# #     Device.sensor_type == "inlet" / "outlet"
# #     Device.status      == "active"
# #
# # FIX B — Home page showing near-zero volume when only inlet ESP32 is live:
# #   All home-page queries (_get_outlet_device_ids, zones_daily,
# #   live_flowrate, dashboard_today) previously hard-coded
# #   sensor_type = "outlet".  When the outlet ESP32 is not yet registered
# #   or not publishing, those queries return nothing and every card shows 0.
# #
# #   A new helper _get_primary_device_ids() now returns:
# #     (outlet_device_ids, "outlet")  — if active outlet devices exist
# #     (inlet_device_ids,  "inlet")   — otherwise (fallback)
# #
# #   zones_daily, live_flowrate and dashboard_today use this helper so they
# #   display real data whether the outlet or inlet device is the one sending
# #   readings.  The 30-day historical averages from daily_summaries still
# #   require the aggregation pipeline to have run with that sensor type, so
# #   they may show 0 until historical data builds up.
# #
# # All other endpoints (monthly_report, alerts, notifications) are unchanged.

# from calendar import monthrange
# from datetime import date, datetime, timedelta, timezone
# from itertools import groupby
# from typing import Optional

# from fastapi import APIRouter, Depends, HTTPException, Query
# from pydantic import BaseModel
# from sqlalchemy import select, func, extract, case
# from sqlalchemy.ext.asyncio import AsyncSession

# from auth import get_current_user as _iot_dep
# from database import get_db
# from models import (
#     User, Network, Zone, Device,
#     Reading, DailySummary, Event, ValveLog,
# )
# from leak_service import FLOW_MISMATCH_THRESHOLD_LPM

# router = APIRouter(prefix="/mobile", tags=["mobile"])

# # ─── Shared publish queue (injected by main.py) ───────────────────────────────
# _publish_queue = None

# def set_mobile_publish_queue(q) -> None:
#     global _publish_queue
#     _publish_queue = q


# # ─────────────────────────────────────────────────────────────────────────────
# #  Helpers
# # ─────────────────────────────────────────────────────────────────────────────

# async def _get_user_network(
#     user: User,
#     db: AsyncSession,
#     network_id: Optional[int] = None,
# ) -> Network:
#     query = select(Network).where(Network.owner_id == user.id)
#     if network_id:
#         query = query.where(Network.id == network_id)
#     result = await db.execute(query.limit(1))
#     net = result.scalar_one_or_none()
#     if not net:
#         raise HTTPException(
#             status_code=404,
#             detail="No network found. Register a network first."
#         )
#     return net


# async def _get_outlet_device_ids(network_id: int, db: AsyncSession) -> list[str]:
#     """All active outlet device IDs for a network."""
#     result = await db.execute(
#         select(Device.device_id)
#         .where(
#             Device.network_id  == network_id,
#             Device.sensor_type == "outlet",
#             Device.status      == "active",
#         )
#     )
#     return [row[0] for row in result.all()]


# async def _get_primary_device_ids(
#     network_id: int, db: AsyncSession
# ) -> tuple[list[str], str]:
#     """
#     Returns (device_ids, sensor_type).

#     Prefers outlet devices — they measure per-tap consumption and are the
#     intended source for home-page totals.  Falls back to inlet devices when
#     no active outlet devices are registered, so the home page still shows
#     real data when only the inlet ESP32 is deployed.

#     Callers must pass the returned sensor_type through to every Reading and
#     DailySummary filter so the queries stay consistent.
#     """
#     outlet_ids = await _get_outlet_device_ids(network_id, db)
#     if outlet_ids:
#         return outlet_ids, "outlet"

#     inlet_result = await db.execute(
#         select(Device.device_id).where(
#             Device.network_id  == network_id,
#             Device.sensor_type == "inlet",
#             Device.status      == "active",
#         )
#     )
#     inlet_ids = [row[0] for row in inlet_result.all()]
#     return inlet_ids, "inlet"


# def _days_elapsed_in_month(year: int, month: int) -> int:
#     today = date.today()
#     if today.year == year and today.month == month:
#         return today.day
#     return monthrange(year, month)[1]


# # ─────────────────────────────────────────────────────────────────────────────
# #  GET /mobile/zones/daily
# #
# #  v3.3: uses _get_primary_device_ids so today's per-zone usage is populated
# #  even when only the inlet device is sending readings.
# #  The 30-day daily average still comes from daily_summaries (outlet sensor
# #  type) and will be 0 until aggregation has run for this network.
# # ─────────────────────────────────────────────────────────────────────────────

# @router.get("/zones/daily")
# async def zones_daily(
#     network_id:   Optional[int] = Query(default=None),
#     db:           AsyncSession  = Depends(get_db),
#     current_user: User          = Depends(_iot_dep),
# ):
#     """
#     Per-zone daily usage for the Flutter DailyConsumptionCard.

#     Response shape (list — one item per zone):
#     [
#       {"name": "Bathroom 01", "used": 60.0, "average": 100.0},
#       ...
#     ]
#     """
#     network = await _get_user_network(current_user, db, network_id)
#     today   = date.today()

#     zone_result = await db.execute(
#         select(Zone)
#         .where(Zone.network_id == network.id)
#         .order_by(Zone.zone_type, Zone.zone_id)
#     )
#     zones = zone_result.scalars().all()
#     if not zones:
#         return []

#     zone_id_strings = [z.zone_id for z in zones]

#     # Determine which sensor type has live data for this network
#     _, primary_sensor = await _get_primary_device_ids(network.id, db)

#     # Today's per-zone usage from raw readings (uses primary sensor type)
#     today_result = await db.execute(
#         select(
#             Reading.zone_id,
#             func.max(Reading.total_volume).label("vol_end"),
#             func.min(Reading.total_volume).label("vol_start"),
#         )
#         .join(Device, Reading.device_id == Device.device_id)
#         .where(
#             Device.network_id            == network.id,
#             Reading.sensor_type          == primary_sensor,
#             Reading.zone_id.in_(zone_id_strings),
#             func.date(Reading.timestamp) == today,
#         )
#         .group_by(Reading.zone_id)
#     )
#     today_by_zone = {
#         row.zone_id: max(float((row.vol_end or 0) - (row.vol_start or 0)), 0.0)
#         for row in today_result.all()
#     }

#     # 30-day daily average from daily_summaries (always outlet — what aggregation writes)
#     thirty_days_ago = today - timedelta(days=30)
#     avg_result = await db.execute(
#         select(
#             DailySummary.zone_id,
#             func.avg(DailySummary.total_volume_litres).label("daily_avg"),
#         )
#         .where(
#             DailySummary.zone_id.in_(zone_id_strings),
#             DailySummary.sensor_type  == "outlet",
#             DailySummary.summary_date >= thirty_days_ago,
#             DailySummary.summary_date <  today,
#             DailySummary.reading_count > 0,
#         )
#         .group_by(DailySummary.zone_id)
#     )
#     avg_by_zone = {
#         row.zone_id: float(row.daily_avg or 0)
#         for row in avg_result.all()
#     }

#     return [
#         {
#             "name":      zone.zone_name,
#             "used":      round(today_by_zone.get(zone.zone_id, 0.0), 2),
#             "average":   round(avg_by_zone.get(zone.zone_id, 0.0),   2),
#             "zone_id":   zone.zone_id,
#             "zone_type": zone.zone_type,
#             "floor":     zone.floor,
#         }
#         for zone in zones
#     ]


# # ─────────────────────────────────────────────────────────────────────────────
# #  GET /mobile/flowrate
# #
# #  v3.3: uses _get_primary_device_ids so the flow rate is populated even
# #  when only the inlet device is sending data.
# # ─────────────────────────────────────────────────────────────────────────────

# @router.get("/flowrate")
# async def live_flowrate(
#     network_id:   Optional[int] = Query(default=None),
#     db:           AsyncSession  = Depends(get_db),
#     current_user: User          = Depends(_iot_dep),
# ):
#     """Live flow rate for the WaterStatusCard."""
#     network = await _get_user_network(current_user, db, network_id)

#     _, primary_sensor = await _get_primary_device_ids(network.id, db)

#     result = await db.execute(
#         select(Reading.flow_rate, Reading.device_id, Reading.timestamp,
#                Device.valve_state)
#         .join(Device, Reading.device_id == Device.device_id)
#         .where(
#             Device.network_id      == network.id,
#             Device.sensor_type     == primary_sensor,
#             Device.status          == "active",
#             Reading.sensor_type    == primary_sensor,
#         )
#         .order_by(Reading.timestamp.desc())
#         .limit(1)
#     )
#     row = result.one_or_none()

#     if row is None:
#         return {
#             "flow_rate":   0.0,
#             "valve_state": "unknown",
#             "unit":        "L/min",
#             "device_id":   None,
#             "timestamp":   None,
#         }

#     return {
#         "flow_rate":   round(float(row.flow_rate), 2),
#         "valve_state": row.valve_state,
#         "unit":        "L/min",
#         "device_id":   row.device_id,
#         "timestamp":   row.timestamp.isoformat(),
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# #  GET /mobile/dashboard/today
# #
# #  v3.3: uses _get_primary_device_ids so litresUsed, dailyAverage and percent
# #  are populated even when only the inlet device is sending readings.
# #
# #  FIX (v3.1.1, unchanged): today's volume uses restart-safe consecutive-
# #  delta odometer instead of max-min so ESP32 reboots don't inflate totals.
# # ─────────────────────────────────────────────────────────────────────────────

# @router.get("/dashboard/today")
# async def dashboard_today(
#     network_id:   Optional[int] = Query(default=None),
#     db:           AsyncSession  = Depends(get_db),
#     current_user: User          = Depends(_iot_dep),
# ):
#     """
#     Today's total usage for the TodayCard.

#     Response shape:
#     {
#       "litresUsed":   220.0,
#       "dailyAverage": 460.0,
#       "percent":      47.8,
#       "active_leaks": 1,
#       "date":         "2026-04-18"
#     }
#     """
#     network = await _get_user_network(current_user, db, network_id)
#     today   = date.today()

#     device_ids, primary_sensor = await _get_primary_device_ids(network.id, db)

#     if not device_ids:
#         return {
#             "litresUsed": 0.0, "dailyAverage": 0.0,
#             "percent": 0.0, "active_leaks": 0,
#             "date": today.isoformat(),
#         }

#     # ── Step 1: today's daily_summaries (only present if aggregation ran) ──
#     summary_result = await db.execute(
#         select(func.sum(DailySummary.total_volume_litres).label("total"))
#         .where(
#             DailySummary.device_id.in_(device_ids),
#             DailySummary.sensor_type  == primary_sensor,
#             DailySummary.summary_date == today,
#             DailySummary.reading_count > 0,
#         )
#     )
#     summary_total = summary_result.scalar()

#     if summary_total is not None:
#         litres_used = float(summary_total)
#     else:
#         # ── Step 2: restart-safe consecutive-delta odometer ────────────────
#         raw_result = await db.execute(
#             select(Reading.device_id, Reading.total_volume, Reading.timestamp)
#             .where(
#                 Reading.device_id.in_(device_ids),
#                 Reading.sensor_type          == primary_sensor,
#                 func.date(Reading.timestamp) == today,
#             )
#             .order_by(Reading.device_id, Reading.timestamp.asc())
#         )
#         raw_rows = raw_result.all()

#         litres_used = 0.0
#         for _dev_id, readings in groupby(raw_rows, key=lambda r: r.device_id):
#             readings_list = list(readings)
#             for i in range(1, len(readings_list)):
#                 delta = (float(readings_list[i].total_volume)
#                          - float(readings_list[i - 1].total_volume))
#                 if delta > 0:
#                     litres_used += delta

#     # ── Step 3: 30-day historical daily average ────────────────────────────
#     thirty_days_ago = today - timedelta(days=30)
#     avg_result = await db.execute(
#         select(func.avg(DailySummary.total_volume_litres))
#         .where(
#             DailySummary.device_id.in_(device_ids),
#             DailySummary.sensor_type  == primary_sensor,
#             DailySummary.summary_date >= thirty_days_ago,
#             DailySummary.summary_date <  today,
#             DailySummary.reading_count > 0,
#         )
#     )
#     daily_avg = float(avg_result.scalar() or 0.0)
#     percent   = round((litres_used / daily_avg * 100) if daily_avg > 0 else 0.0, 1)
#     percent   = min(percent, 200.0)

#     # ── Active leaks (unresolved today) ───────────────────────────────────
#     leak_result = await db.execute(
#         select(func.count()).where(
#             Event.device_id.in_(device_ids),
#             Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
#             Event.resolved == False,
#             func.date(Event.timestamp) == today,
#         )
#     )
#     active_leaks = int(leak_result.scalar() or 0)

#     return {
#         "litresUsed":   round(litres_used, 2),
#         "dailyAverage": round(daily_avg,   2),
#         "percent":      percent,
#         "active_leaks": active_leaks,
#         "date":         today.isoformat(),
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# #  GET /mobile/leakages
# #
# #  v3.2: valve_state sourced from inlet device (where physical relay lives).
# #  v3.3: added Device.sensor_type + Device.status filters to both inlet and
# #        outlet outer queries. Without these, the zone_id join could silently
# #        match the wrong device in a zone and the timestamp equality condition
# #        would find no rows, causing one or both flow values to show 0.0.
# # ─────────────────────────────────────────────────────────────────────────────

# @router.get("/leakages")
# async def leakages(
#     network_id:   Optional[int] = Query(default=None),
#     db:           AsyncSession  = Depends(get_db),
#     current_user: User          = Depends(_iot_dep),
# ):
#     """
#     All zones with live IN/OUT flow and valve state for the Leakages screen.
#     valve_state reflects the inlet device (where the physical relay lives).
#     """
#     network = await _get_user_network(current_user, db, network_id)

#     # ── Query 1: all zones ────────────────────────────────────────────────
#     zone_result = await db.execute(
#         select(Zone)
#         .where(Zone.network_id == network.id)
#         .order_by(Zone.zone_type, Zone.zone_id)
#     )
#     zones = zone_result.scalars().all()
#     if not zones:
#         return []

#     zone_ids = [z.id for z in zones]

#     # ── Query 2: latest inlet flow_rate per zone ──────────────────────────
#     inlet_sub = (
#         select(
#             Device.zone_id,
#             func.max(Reading.timestamp).label("latest_ts"),
#         )
#         .join(Reading, Reading.device_id == Device.device_id)
#         .where(
#             Device.zone_id.in_(zone_ids),
#             Device.sensor_type == "inlet",
#             Device.status      == "active",
#             Reading.sensor_type == "inlet",
#         )
#         .group_by(Device.zone_id)
#         .subquery()
#     )
#     inlet_result = await db.execute(
#         select(Device.zone_id, Reading.flow_rate)
#         .join(Reading, Reading.device_id == Device.device_id)
#         .join(
#             inlet_sub,
#             (inlet_sub.c.zone_id   == Device.zone_id) &
#             (inlet_sub.c.latest_ts == Reading.timestamp),
#         )
#         .where(
#             Reading.sensor_type == "inlet",
#             Device.sensor_type  == "inlet",   # ← v3.3 fix: prevent wrong-device match
#             Device.status       == "active",
#         )
#     )
#     inlet_by_zone: dict[int, float] = {}
#     for row in inlet_result.all():
#         if row.zone_id not in inlet_by_zone:
#             inlet_by_zone[row.zone_id] = float(row.flow_rate)

#     # ── Query 3: latest outlet flow_rate per zone ─────────────────────────
#     outlet_sub = (
#         select(
#             Device.zone_id,
#             func.max(Reading.timestamp).label("latest_ts"),
#         )
#         .join(Reading, Reading.device_id == Device.device_id)
#         .where(
#             Device.zone_id.in_(zone_ids),
#             Device.sensor_type  == "outlet",
#             Device.status       == "active",
#             Reading.sensor_type == "outlet",
#         )
#         .group_by(Device.zone_id)
#         .subquery()
#     )
#     outlet_result = await db.execute(
#         select(Device.zone_id, Reading.flow_rate)
#         .join(Reading, Reading.device_id == Device.device_id)
#         .join(
#             outlet_sub,
#             (outlet_sub.c.zone_id   == Device.zone_id) &
#             (outlet_sub.c.latest_ts == Reading.timestamp),
#         )
#         .where(
#             Reading.sensor_type == "outlet",
#             Device.sensor_type  == "outlet",  # ← v3.3 fix: prevent wrong-device match
#             Device.status       == "active",
#         )
#     )
#     outlet_flow_by_zone: dict[int, float] = {}
#     for row in outlet_result.all():
#         if row.zone_id not in outlet_flow_by_zone:
#             outlet_flow_by_zone[row.zone_id] = float(row.flow_rate)

#     # ── Query 4: inlet device valve_state per zone (source of truth) ──────
#     # Device.valve_state on the inlet device is updated by:
#     #   • POST /mobile/valve       (user manual command)
#     #   • _process_valve_status()  (ESP32 valve/status ACK)
#     #   • _process_event_message() (ESP32 leak/alert with valve=CLOSED)
#     inlet_valve_result = await db.execute(
#         select(Device.zone_id, Device.valve_state)
#         .where(
#             Device.zone_id.in_(zone_ids),
#             Device.sensor_type == "inlet",
#             Device.status      == "active",
#         )
#     )
#     inlet_valve_by_zone: dict[int, str] = {}
#     for row in inlet_valve_result.all():
#         if row.zone_id not in inlet_valve_by_zone:
#             inlet_valve_by_zone[row.zone_id] = row.valve_state or "unknown"

#     # ── Build response ────────────────────────────────────────────────────
#     response = []
#     for zone in zones:
#         in_flow     = inlet_by_zone.get(zone.id, 0.0)
#         out_flow    = outlet_flow_by_zone.get(zone.id, 0.0)
#         valve_state = inlet_valve_by_zone.get(zone.id, "unknown")

#         leak = (in_flow - out_flow) >= FLOW_MISMATCH_THRESHOLD_LPM and valve_state == "open"

#         if leak:
#             ui_state = "leak_detected"
#         elif valve_state == "closed":
#             ui_state = "valve_closed"
#         else:
#             ui_state = "normal"

#         response.append({
#             "zone_id":     zone.id,
#             "zone_slug":   zone.zone_id,
#             "zone_name":   zone.zone_name,
#             "zone_type":   zone.zone_type,
#             "floor":       zone.floor,
#             "inFlow":      round(in_flow,  2),
#             "outFlow":     round(out_flow, 2),
#             "valve_state": valve_state,
#             "leak":        leak,
#             "ui_state":    ui_state,
#         })

#     return response


# # ─────────────────────────────────────────────────────────────────────────────
# #  POST /mobile/valve
# #
# #  v3.2: removed 409/override. Opening while leak is active auto-resolves
# #  alerts and resets LeakDetectionService state. Unchanged in v3.3.
# # ─────────────────────────────────────────────────────────────────────────────

# class ValveCommandBody(BaseModel):
#     zone_id:  int
#     action:   str
#     override: bool = False   # kept for client compatibility; no longer used


# @router.post("/valve")
# async def mobile_valve_command(
#     body:         ValveCommandBody,
#     db:           AsyncSession = Depends(get_db),
#     current_user: User         = Depends(_iot_dep),
# ):
#     """
#     Send open/close command to all inlet devices in a zone.
#     The physical relay is on the inlet ESP32; outlet devices are not commanded.
#     Opening while a leak alert is active auto-resolves the alert.
#     """
#     if body.action not in ("open", "close"):
#         raise HTTPException(status_code=400, detail="action must be 'open' or 'close'")

#     zone_result = await db.execute(
#         select(Zone)
#         .join(Network, Zone.network_id == Network.id)
#         .where(Zone.id == body.zone_id, Network.owner_id == current_user.id)
#     )
#     zone = zone_result.scalar_one_or_none()
#     if not zone:
#         raise HTTPException(status_code=404, detail="Zone not found")

#     # Auto-resolve active leak alerts when user opens the valve
#     if body.action == "open":
#         leak_events_result = await db.execute(
#             select(Event).where(
#                 Event.zone_id    == body.zone_id,
#                 Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
#                 Event.resolved   == False,
#             )
#         )
#         leak_events = leak_events_result.scalars().all()
#         for event in leak_events:
#             event.resolved    = True
#             event.resolved_at = datetime.now(timezone.utc)

#         from leak_service import get_leak_service
#         svc = get_leak_service()
#         if svc:
#             await svc.clear_leak(body.zone_id)
#             await svc.clear_valve_failure(body.zone_id)

#     net_result = await db.execute(
#         select(Network).where(Network.id == zone.network_id)
#     )
#     network = net_result.scalar_one()

#     inlet_result = await db.execute(
#         select(Device)
#         .where(
#             Device.zone_id     == body.zone_id,
#             Device.sensor_type == "inlet",
#             Device.status      == "active",
#         )
#     )
#     inlet_devices = inlet_result.scalars().all()
#     if not inlet_devices:
#         raise HTTPException(status_code=404, detail="No active inlet devices in zone")

#     sent = []
#     for device in inlet_devices:
#         device.valve_state = body.action
#         db.add(ValveLog(
#             device_id    = device.device_id,
#             commanded_by = current_user.id,
#             action       = body.action,
#             source       = "manual",
#         ))
#         db.add(Event(
#             device_id   = device.device_id,
#             network_id  = device.network_id,
#             zone_id     = device.zone_id,
#             event_type  = f"valve_{body.action}d",
#             description = f"Valve manually {body.action}d via mobile app "
#                           f"by user {current_user.id}.",
#         ))
#         if _publish_queue:
#             await _publish_queue.put(
#                 (network.network_id, zone.zone_id, device.device_id, body.action)
#             )
#         sent.append(device.device_id)

#     await db.commit()

#     return {
#         "status":    "commands_sent",
#         "zone_id":   body.zone_id,
#         "zone_name": zone.zone_name,
#         "action":    body.action,
#         "devices":   sent,
#         "count":     len(sent),
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# #  GET /mobile/report/monthly  — UNCHANGED
# # ─────────────────────────────────────────────────────────────────────────────

# @router.get("/report/monthly")
# async def monthly_report(
#     year:         int           = Query(default=datetime.now(timezone.utc).year),
#     month:        int           = Query(default=datetime.now(timezone.utc).month, ge=1, le=12),
#     network_id:   Optional[int] = Query(default=None),
#     db:           AsyncSession  = Depends(get_db),
#     current_user: User          = Depends(_iot_dep),
# ):
#     """Monthly report for the Report screen year/month dropdown."""
#     network    = await _get_user_network(current_user, db, network_id)
#     device_ids = await _get_outlet_device_ids(network.id, db)

#     if not device_ids:
#         return {
#             "year": year, "month": month,
#             "total_usage_L": 0.0, "weekly_avg_L": 0.0,
#             "daily_avg_L": 0.0, "leaks_detected": 0, "days_with_data": 0,
#         }

#     result = await db.execute(
#         select(
#             func.sum(DailySummary.total_volume_litres).label("total"),
#             func.count(DailySummary.id).label("days"),
#             func.sum(DailySummary.leak_event_count).label("leaks"),
#         )
#         .where(
#             DailySummary.device_id.in_(device_ids),
#             DailySummary.sensor_type == "outlet",
#             extract("year",  DailySummary.summary_date) == year,
#             extract("month", DailySummary.summary_date) == month,
#             DailySummary.reading_count > 0,
#         )
#     )
#     row        = result.one()
#     total      = float(row.total or 0)
#     days       = int(row.days   or 0) or 1
#     leaks      = int(row.leaks  or 0)
#     daily_avg  = total / days
#     weekly_avg = total / max(days / 7, 1)

#     return {
#         "year":           year,
#         "month":          month,
#         "total_usage_L":  round(total,      2),
#         "weekly_avg_L":   round(weekly_avg, 2),
#         "daily_avg_L":    round(daily_avg,  2),
#         "leaks_detected": leaks,
#         "days_with_data": days,
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# #  GET /mobile/alerts  — UNCHANGED
# # ─────────────────────────────────────────────────────────────────────────────

# @router.get("/alerts")
# async def mobile_alerts(
#     resolved:     bool          = Query(default=False),
#     network_id:   Optional[int] = Query(default=None),
#     limit:        int           = Query(default=50, le=200),
#     db:           AsyncSession  = Depends(get_db),
#     current_user: User          = Depends(_iot_dep),
# ):
#     """Leak alert list for the notification bell screen."""
#     network    = await _get_user_network(current_user, db, network_id)
#     device_ids = await _get_outlet_device_ids(network.id, db)

#     if not device_ids:
#         return {"unread_count": 0, "items": []}

#     zone_result = await db.execute(
#         select(Zone).where(Zone.network_id == network.id)
#     )
#     zone_map = {z.id: z.zone_name for z in zone_result.scalars()}

#     dev_zone_result = await db.execute(
#         select(Device.device_id, Device.zone_id)
#         .where(Device.device_id.in_(device_ids))
#     )
#     dev_zone_map = {row.device_id: row.zone_id for row in dev_zone_result.all()}

#     unread_result = await db.execute(
#         select(func.count()).where(
#             Event.device_id.in_(device_ids),
#             Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
#             Event.resolved == False,
#         )
#     )
#     unread_count = int(unread_result.scalar() or 0)

#     query = (
#         select(Event)
#         .where(
#             Event.device_id.in_(device_ids),
#             Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
#             Event.resolved == resolved,
#         )
#         .order_by(Event.timestamp.desc())
#         .limit(limit)
#     )
#     result = await db.execute(query)
#     events = result.scalars().all()

#     return {
#         "unread_count": unread_count,
#         "items": [
#             {
#                 "id":          e.id,
#                 "zone_name":   zone_map.get(dev_zone_map.get(e.device_id), "Unknown Zone"),
#                 "device_id":   e.device_id,
#                 "event_type":  e.event_type,
#                 "description": e.description,
#                 "resolved":    e.resolved,
#                 "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
#                 "timestamp":   e.timestamp.isoformat(),
#             }
#             for e in events
#         ],
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# #  POST /mobile/alerts/{alert_id}/resolve  — UNCHANGED
# # ─────────────────────────────────────────────────────────────────────────────

# @router.post("/alerts/{alert_id}/resolve")
# async def resolve_alert(
#     alert_id:     int,
#     db:           AsyncSession = Depends(get_db),
#     current_user: User         = Depends(_iot_dep),
# ):
#     result = await db.execute(
#         select(Event)
#         .join(Device,  Event.device_id   == Device.device_id)
#         .join(Network, Device.network_id == Network.id)
#         .where(Event.id == alert_id, Network.owner_id == current_user.id)
#     )
#     event = result.scalar_one_or_none()
#     if not event:
#         raise HTTPException(status_code=404, detail="Alert not found")
#     if event.resolved:
#         return {"status": "already_resolved", "alert_id": alert_id}

#     event.resolved    = True
#     event.resolved_at = datetime.now(timezone.utc)
#     await db.commit()

#     from leak_service import get_leak_service
#     svc = get_leak_service()
#     if svc and event.zone_id:
#         await svc.clear_leak(event.zone_id)
#         if event.event_type == "valve_failure":
#             await svc.clear_valve_failure(event.zone_id)

#     return {
#         "status":      "resolved",
#         "alert_id":    alert_id,
#         "resolved_at": event.resolved_at.isoformat(),
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# #  GET /mobile/notifications  — UNCHANGED
# # ─────────────────────────────────────────────────────────────────────────────

# @router.get("/notifications")
# async def get_notifications(
#     network_id:   Optional[int] = Query(default=None),
#     db:           AsyncSession  = Depends(get_db),
#     current_user: User          = Depends(_iot_dep),
# ):
#     """
#     Returns notifications for leak events where the valve was auto-closed.
#     Flutter BellButton calls this every 15 seconds.
#     """
#     network    = await _get_user_network(current_user, db, network_id)
#     device_ids = await _get_outlet_device_ids(network.id, db)

#     if not device_ids:
#         return []

#     zone_result = await db.execute(
#         select(Zone).where(Zone.network_id == network.id)
#     )
#     zone_map = {z.id: z.zone_name for z in zone_result.scalars()}

#     dev_zone_result = await db.execute(
#         select(Device.device_id, Device.zone_id)
#         .where(Device.device_id.in_(device_ids))
#     )
#     dev_zone_map = {row.device_id: row.zone_id for row in dev_zone_result.all()}

#     events_result = await db.execute(
#         select(Event)
#         .where(
#             Event.device_id.in_(device_ids),
#             Event.event_type == "leak_detected",
#             Event.resolved   == False,
#         )
#         .order_by(Event.timestamp.desc())
#         .limit(20)
#     )
#     events = events_result.scalars().all()

#     now           = datetime.now(timezone.utc)
#     notifications = []

#     for event in events:
#         valve_result = await db.execute(
#             select(ValveLog)
#             .where(
#                 ValveLog.device_id == event.device_id,
#                 ValveLog.source    == "auto_leak",
#                 ValveLog.action    == "close",
#             )
#             .order_by(ValveLog.commanded_at.desc())
#             .limit(1)
#         )
#         if valve_result.scalar_one_or_none() is None:
#             continue

#         diff = (now - event.timestamp).total_seconds()
#         if diff < 60:
#             time_str = "Just now"
#         elif diff < 3600:
#             time_str = f"{int(diff / 60)} mins ago"
#         elif diff < 86400:
#             time_str = f"{int(diff / 3600)} hrs ago"
#         else:
#             time_str = f"{int(diff / 86400)} days ago"

#         zone_name = zone_map.get(dev_zone_map.get(event.device_id), "Unknown Zone")

#         notifications.append({
#             "title":            f"Leak Detected: {zone_name}",
#             "message":          (
#                 f"Leak detected in {zone_name} pipeline. "
#                 f"Valve has been automatically closed. "
#                 f"Please check the pipeline immediately."
#             ),
#             "type":             "leak",
#             "time":             time_str,
#             "target_tab_index": 1,
#         })

#     return notifications

# mobile_router.py
# AquaSense v3.4 — Mobile API Router
#
# All endpoints the Flutter app calls directly.
#
# Changes v3.4 — False leak detection after valve opening (POST /mobile/valve only):
#
#   ROOT CAUSE:
#     _process_inlet_reading() in mqtt_service.py passes device.valve_state
#     from the in-process device cache (TTL = 60 s) to
#     LeakDetectionService.update_valve_state(). When the user manually
#     closes the valve, the cache still returns the OLD "open" state for up
#     to 60 seconds, so the LeakDetectionService keeps receiving
#     update_valve_state(OPEN) while the valve is physically closed.
#
#     By the time the user re-opens the valve, the LeakDetectionService
#     already thinks valve_state = OPEN (from the stale cache). When
#     _process_valve_status("Opened") then calls update_valve_state(OPEN),
#     there is no state TRANSITION (OPEN → OPEN), so NO settle window is
#     started. Inlet flow rises immediately, outlet lags, delta > threshold
#     for 3 consecutive seconds → false leak triggered.
#
#   FIX (two parts, both in mobile_valve_command):
#
#   Part 1 — Force settle window immediately on open:
#     Call svc.force_settle(zone_id) right after clearing leak/failure state.
#     force_settle() unconditionally sets valve_state=OPEN and starts the
#     settle window, bypassing the "transition required" guard in
#     update_valve_state(). This mirrors the ESP32 behaviour exactly:
#       if (cmd == "open") { isSettling = true; settleStartMillis = millis(); }
#     The settle window is now guaranteed regardless of what in-memory state
#     the service was in.
#
#   Part 2 — Invalidate device cache for inlet devices:
#     Call invalidate_device_cache(device_id) for every inlet device after
#     updating device.valve_state in the DB. This forces the next call to
#     _process_inlet_reading() to fetch the fresh "open" state from the DB,
#     eliminating the stale-cache CLOSED→OPEN→CLOSED churn that was
#     cancelling the settle window started by _process_valve_status().
#
#   All other endpoints are unchanged from v3.3.

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from itertools import groupby
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user as _iot_dep
from database import get_db
from models import (
    User, Network, Zone, Device,
    Reading, DailySummary, Event, ValveLog,
)
from leak_service import FLOW_MISMATCH_THRESHOLD_LPM

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


async def _get_primary_device_ids(
    network_id: int, db: AsyncSession
) -> tuple[list[str], str]:
    """
    Returns (device_ids, sensor_type).

    Prefers outlet devices. Falls back to inlet devices when no active outlet
    devices are registered, so the home page shows real data when only the
    inlet ESP32 is deployed.
    """
    outlet_ids = await _get_outlet_device_ids(network_id, db)
    if outlet_ids:
        return outlet_ids, "outlet"

    inlet_result = await db.execute(
        select(Device.device_id).where(
            Device.network_id  == network_id,
            Device.sensor_type == "inlet",
            Device.status      == "active",
        )
    )
    inlet_ids = [row[0] for row in inlet_result.all()]
    return inlet_ids, "inlet"


def _days_elapsed_in_month(year: int, month: int) -> int:
    today = date.today()
    if today.year == year and today.month == month:
        return today.day
    return monthrange(year, month)[1]


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/zones/daily  — UNCHANGED from v3.3
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zones/daily")
async def zones_daily(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    Per-zone daily usage for the Flutter DailyConsumptionCard.

    Response shape (list — one item per zone):
    [
      {"name": "Bathroom 01", "used": 60.0, "average": 100.0},
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

    _, primary_sensor = await _get_primary_device_ids(network.id, db)

    today_result = await db.execute(
        select(
            Reading.zone_id,
            func.max(Reading.total_volume).label("vol_end"),
            func.min(Reading.total_volume).label("vol_start"),
        )
        .join(Device, Reading.device_id == Device.device_id)
        .where(
            Device.network_id            == network.id,
            Reading.sensor_type          == primary_sensor,
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
            DailySummary.sensor_type  == "outlet",
            DailySummary.summary_date >= thirty_days_ago,
            DailySummary.summary_date <  today,
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
            "average":   round(avg_by_zone.get(zone.zone_id, 0.0),   2),
            "zone_id":   zone.zone_id,
            "zone_type": zone.zone_type,
            "floor":     zone.floor,
        }
        for zone in zones
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/flowrate  — UNCHANGED from v3.3
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/flowrate")
async def live_flowrate(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """Live flow rate for the WaterStatusCard."""
    network = await _get_user_network(current_user, db, network_id)

    _, primary_sensor = await _get_primary_device_ids(network.id, db)

    result = await db.execute(
        select(Reading.flow_rate, Reading.device_id, Reading.timestamp,
               Device.valve_state)
        .join(Device, Reading.device_id == Device.device_id)
        .where(
            Device.network_id      == network.id,
            Device.sensor_type     == primary_sensor,
            Device.status          == "active",
            Reading.sensor_type    == primary_sensor,
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
#  GET /mobile/dashboard/today  — UNCHANGED from v3.3
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
      "date":         "2026-04-19"
    }
    """
    network = await _get_user_network(current_user, db, network_id)
    today   = date.today()

    device_ids, primary_sensor = await _get_primary_device_ids(network.id, db)

    if not device_ids:
        return {
            "litresUsed": 0.0, "dailyAverage": 0.0,
            "percent": 0.0, "active_leaks": 0,
            "date": today.isoformat(),
        }

    summary_result = await db.execute(
        select(func.sum(DailySummary.total_volume_litres).label("total"))
        .where(
            DailySummary.device_id.in_(device_ids),
            DailySummary.sensor_type  == primary_sensor,
            DailySummary.summary_date == today,
            DailySummary.reading_count > 0,
        )
    )
    summary_total = summary_result.scalar()

    if summary_total is not None:
        litres_used = float(summary_total)
    else:
        raw_result = await db.execute(
            select(Reading.device_id, Reading.total_volume, Reading.timestamp)
            .where(
                Reading.device_id.in_(device_ids),
                Reading.sensor_type          == primary_sensor,
                func.date(Reading.timestamp) == today,
            )
            .order_by(Reading.device_id, Reading.timestamp.asc())
        )
        raw_rows = raw_result.all()

        litres_used = 0.0
        for _dev_id, readings in groupby(raw_rows, key=lambda r: r.device_id):
            readings_list = list(readings)
            for i in range(1, len(readings_list)):
                delta = (float(readings_list[i].total_volume)
                         - float(readings_list[i - 1].total_volume))
                if delta > 0:
                    litres_used += delta

    thirty_days_ago = today - timedelta(days=30)
    avg_result = await db.execute(
        select(func.avg(DailySummary.total_volume_litres))
        .where(
            DailySummary.device_id.in_(device_ids),
            DailySummary.sensor_type  == primary_sensor,
            DailySummary.summary_date >= thirty_days_ago,
            DailySummary.summary_date <  today,
            DailySummary.reading_count > 0,
        )
    )
    daily_avg = float(avg_result.scalar() or 0.0)
    percent   = round((litres_used / daily_avg * 100) if daily_avg > 0 else 0.0, 1)
    percent   = min(percent, 200.0)

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
        "dailyAverage": round(daily_avg,   2),
        "percent":      percent,
        "active_leaks": active_leaks,
        "date":         today.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/leakages  — UNCHANGED from v3.3
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/leakages")
async def leakages(
    network_id:   Optional[int] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    """
    All zones with live IN/OUT flow and valve state for the Leakages screen.
    valve_state reflects the inlet device (where the physical relay lives).
    """
    network = await _get_user_network(current_user, db, network_id)

    zone_result = await db.execute(
        select(Zone)
        .where(Zone.network_id == network.id)
        .order_by(Zone.zone_type, Zone.zone_id)
    )
    zones = zone_result.scalars().all()
    if not zones:
        return []

    zone_ids = [z.id for z in zones]

    # Query 2: latest inlet flow_rate per zone
    inlet_sub = (
        select(
            Device.zone_id,
            func.max(Reading.timestamp).label("latest_ts"),
        )
        .join(Reading, Reading.device_id == Device.device_id)
        .where(
            Device.zone_id.in_(zone_ids),
            Device.sensor_type  == "inlet",
            Device.status       == "active",
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
        .where(
            Reading.sensor_type == "inlet",
            Device.sensor_type  == "inlet",
            Device.status       == "active",
        )
    )
    inlet_by_zone: dict[int, float] = {}
    for row in inlet_result.all():
        if row.zone_id not in inlet_by_zone:
            inlet_by_zone[row.zone_id] = float(row.flow_rate)

    # Query 3: latest outlet flow_rate per zone
    outlet_sub = (
        select(
            Device.zone_id,
            func.max(Reading.timestamp).label("latest_ts"),
        )
        .join(Reading, Reading.device_id == Device.device_id)
        .where(
            Device.zone_id.in_(zone_ids),
            Device.sensor_type  == "outlet",
            Device.status       == "active",
            Reading.sensor_type == "outlet",
        )
        .group_by(Device.zone_id)
        .subquery()
    )
    outlet_result = await db.execute(
        select(Device.zone_id, Reading.flow_rate)
        .join(Reading, Reading.device_id == Device.device_id)
        .join(
            outlet_sub,
            (outlet_sub.c.zone_id   == Device.zone_id) &
            (outlet_sub.c.latest_ts == Reading.timestamp),
        )
        .where(
            Reading.sensor_type == "outlet",
            Device.sensor_type  == "outlet",
            Device.status       == "active",
        )
    )
    outlet_flow_by_zone: dict[int, float] = {}
    for row in outlet_result.all():
        if row.zone_id not in outlet_flow_by_zone:
            outlet_flow_by_zone[row.zone_id] = float(row.flow_rate)

    # Query 4: inlet device valve_state per zone (source of truth)
    inlet_valve_result = await db.execute(
        select(Device.zone_id, Device.valve_state)
        .where(
            Device.zone_id.in_(zone_ids),
            Device.sensor_type == "inlet",
            Device.status      == "active",
        )
    )
    inlet_valve_by_zone: dict[int, str] = {}
    for row in inlet_valve_result.all():
        if row.zone_id not in inlet_valve_by_zone:
            inlet_valve_by_zone[row.zone_id] = row.valve_state or "unknown"

    response = []
    for zone in zones:
        in_flow     = inlet_by_zone.get(zone.id, 0.0)
        out_flow    = outlet_flow_by_zone.get(zone.id, 0.0)
        valve_state = inlet_valve_by_zone.get(zone.id, "unknown")

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
#
#  v3.4 FIX: false leak detection after valve opening — see module docstring.
#
#  Two additions when action="open":
#    1. svc.force_settle(zone_id)          — start settle window NOW
#    2. invalidate_device_cache(device_id)  — flush stale valve_state from cache
# ─────────────────────────────────────────────────────────────────────────────

class ValveCommandBody(BaseModel):
    zone_id:  int
    action:   str
    override: bool = False   # kept for client compatibility; no longer used


@router.post("/valve")
async def mobile_valve_command(
    body:         ValveCommandBody,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    """
    Send open/close command to all inlet devices in a zone.

    When action="open":
      1. Active leak/valve-failure alerts for the zone are auto-resolved
         (toggling open = user acknowledges the leak is physically fixed).
      2. svc.force_settle() starts the settle window in the server backup
         detector IMMEDIATELY — before the MQTT command even reaches the
         ESP32 — so inlet flow rising during the physical delay between relay
         energise and outlet reading update never triggers a false leak.
      3. invalidate_device_cache() clears the stale cached valve_state for
         each inlet device, so the next _process_inlet_reading() call reads
         the fresh "open" state from the DB instead of continuing to feed
         the old "closed" state to update_valve_state().
    """
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

    # ── action = "open": resolve alerts + start settle window ─────────────
    if body.action == "open":
        # Auto-resolve any active leak/valve-failure alerts for this zone
        leak_events_result = await db.execute(
            select(Event).where(
                Event.zone_id    == body.zone_id,
                Event.event_type.in_(["leak_detected", "flow_mismatch", "valve_failure"]),
                Event.resolved   == False,
            )
        )
        for event in leak_events_result.scalars().all():
            event.resolved    = True
            event.resolved_at = datetime.now(timezone.utc)

        from leak_service import get_leak_service
        from models import ValveState as VS
        svc = get_leak_service()
        if svc:
            # Clear alert flags in the in-memory state machine
            await svc.clear_leak(body.zone_id)
            await svc.clear_valve_failure(body.zone_id)

            # ── v3.4 FIX Part 1: unconditionally start the settle window ───
            # This bypasses the "transition required" guard in
            # update_valve_state() and guarantees the 10-second suppression
            # window starts at the instant the user taps open, not when the
            # ESP32 ACK arrives (which may be a second or two later).
            svc.force_settle(body.zone_id)

    net_result = await db.execute(
        select(Network).where(Network.id == zone.network_id)
    )
    network = net_result.scalar_one()

    # The physical relay is wired to the INLET ESP32 — only inlet devices
    # subscribe to the valve/command topic and control the solenoid.
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
            await _publish_queue.put(
                (network.network_id, zone.zone_id, device.device_id, body.action)
            )
        sent.append(device.device_id)

    await db.commit()

    # ── v3.4 FIX Part 2: invalidate device cache after DB commit ──────────
    # The mqtt_service device cache (TTL = 60 s) still holds the OLD
    # valve_state. _process_inlet_reading() reads this cached state and
    # passes it to update_valve_state(), which can cancel the settle window
    # started above by causing a spurious OPEN→CLOSED→OPEN transition.
    # Invalidating the cache forces the next inlet reading to re-fetch the
    # fresh "open" state from the DB, eliminating the churn.
    if body.action == "open":
        from mqtt_service import invalidate_device_cache
        for device in inlet_devices:
            invalidate_device_cache(device.device_id)

    return {
        "status":    "commands_sent",
        "zone_id":   body.zone_id,
        "zone_name": zone.zone_name,
        "action":    body.action,
        "devices":   sent,
        "count":     len(sent),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/report/monthly  — UNCHANGED
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
        "year":           year,
        "month":          month,
        "total_usage_L":  round(total,      2),
        "weekly_avg_L":   round(weekly_avg, 2),
        "daily_avg_L":    round(daily_avg,  2),
        "leaks_detected": leaks,
        "days_with_data": days,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /mobile/alerts  — UNCHANGED
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
#  POST /mobile/alerts/{alert_id}/resolve  — UNCHANGED
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id:     int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
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
#  GET /mobile/notifications  — UNCHANGED
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
    """
    network    = await _get_user_network(current_user, db, network_id)
    device_ids = await _get_outlet_device_ids(network.id, db)

    if not device_ids:
        return []

    zone_result = await db.execute(
        select(Zone).where(Zone.network_id == network.id)
    )
    zone_map = {z.id: z.zone_name for z in zone_result.scalars()}

    dev_zone_result = await db.execute(
        select(Device.device_id, Device.zone_id)
        .where(Device.device_id.in_(device_ids))
    )
    dev_zone_map = {row.device_id: row.zone_id for row in dev_zone_result.all()}

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
            continue

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
            "target_tab_index": 1,
        })

    return notifications
