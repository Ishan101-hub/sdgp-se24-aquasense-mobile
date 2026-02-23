# main.py
# =============================================================
#  AquaSense — FastAPI Backend
#
#  Endpoints mapped to each frontend screen:
#
#  HOME SCREEN
#    GET  /dashboard/{user_id}/{device_id}   → live summary card
#
#  LEAKAGES SCREEN
#    GET  /leakages/{user_id}/{device_id}    → per-zone inlet/outlet status
#    POST /valve/command                     → open/close valve
#    GET  /valve/logs/{user_id}/{device_id}  → valve history
#
#  REPORT SCREEN
#    GET  /report/monthly                    → monthly totals + leak count
#
#  HOME CHART (monthly/weekly/daily toggle)
#    GET  /analytics/daily                   → daily usage list for chart
#
#  ALERTS / NOTIFICATION BELL
#    GET  /alerts/{user_id}                  → list open alerts
#    POST /alerts/{alert_id}/resolve         → mark alert resolved
#
#  DEVICES (online/offline status)
#    GET  /devices/{user_id}                 → device heartbeat status
#
#  SETTINGS
#    GET  /health                            → server status check
# =============================================================

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import (
    readings_col, events_col, alerts_col,
    valve_log_col, devices_col, ensure_indexes
)
from mqtt_worker import start_mqtt, stop_mqtt, publish_valve_command


# ─── App lifecycle ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    start_mqtt()
    yield
    stop_mqtt()


app = FastAPI(
    title="AquaSense API",
    description="Smart Water Monitoring — REST API",
    version="2.0.0",
    lifespan=lifespan,
)

# Allow Flutter app to call this API from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ─────────────────────────────────────────────────
def _now():
    return datetime.now(timezone.utc)


def _bson_safe(doc: dict) -> dict:
    """Convert ObjectId to string so FastAPI can serialise it."""
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def _get_latest_reading(user_id: str, device_id: str, node: str) -> dict | None:
    """Return the most recent reading document for a given node."""
    return readings_col.find_one(
        {"user_id": user_id, "device_id": device_id, "node": node},
        {"_id": 0},
        sort=[("ts_ingested", -1)],
    )


# ─────────────────────────────────────────────────────────────
#  HEALTH
# ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health():
    """
    Used by Settings screen to verify server connectivity.
    Returns server status and current UTC time.
    """
    return {
        "status":  "online",
        "message": "AquaSense server is running",
        "ts":      _now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
#  HOME SCREEN — /dashboard
#  Provides everything the Home screen needs in one call:
#    • Today's total water used
#    • Current live flow rate (L/min)
#    • Valve status (open/closed)
#    • Leak detection status
#    • % of daily average
#    • Device online/offline
# ─────────────────────────────────────────────────────────────
@app.get("/dashboard/{user_id}/{device_id}", tags=["Home"])
def get_dashboard(user_id: str, device_id: str):
    """
    HOME SCREEN — Single endpoint that returns everything
    the dashboard needs. Flutter calls this once on load
    and every 2 seconds for live updates.
    """
    inlet  = _get_latest_reading(user_id, device_id, "inlet")
    outlet = _get_latest_reading(user_id, device_id, "outlet")
    device = devices_col.find_one(
        {"user_id": user_id, "device_id": device_id},
        {"_id": 0}
    )

    # Determine online status from heartbeat (offline if >90s ago)
    online = False
    if device and device.get("last_seen"):
        online = (_now() - device["last_seen"]).total_seconds() < 90

    # Today's total = current total minus what it was at midnight
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_reading = readings_col.find_one(
        {"user_id": user_id, "device_id": device_id, "node": "inlet",
         "ts_ingested": {"$gte": today_start}},
        sort=[("ts_ingested", 1)]   # oldest reading today = closest to midnight
    )
    today_total_L = 0.0
    if inlet and midnight_reading:
        today_total_L = max(
            0.0,
            float(inlet.get("total_L", 0)) - float(midnight_reading.get("total_L", 0))
        )
    elif inlet:
        today_total_L = float(inlet.get("total_L", 0))

    # Historical daily average from last 30 days
    thirty_days_ago = _now() - timedelta(days=30)
    pipeline = [
        {"$match": {
            "user_id": user_id, "device_id": device_id, "node": "inlet",
            "ts_ingested": {"$gte": thirty_days_ago}
        }},
        {"$group": {
            "_id": {
                "y": {"$year": "$ts_ingested"},
                "m": {"$month": "$ts_ingested"},
                "d": {"$dayOfMonth": "$ts_ingested"},
            },
            "max_L": {"$max": "$total_L"},
            "min_L": {"$min": "$total_L"},
        }},
        {"$project": {"day_usage": {"$subtract": ["$max_L", "$min_L"]}}},
    ]
    daily_usages  = list(readings_col.aggregate(pipeline))
    daily_avg_L   = (
        sum(d["day_usage"] for d in daily_usages) / len(daily_usages)
        if daily_usages else 460.0  # sensible default if no history
    )

    pct_of_avg = round((today_total_L / daily_avg_L * 100), 1) if daily_avg_L > 0 else 0

    return {
        # ── Live flow ──────────────────────────────────────────
        "flow_rate_lpm":  float(inlet.get("flow_rate", 0))   if inlet  else 0.0,
        "outlet_flow_lpm":float(outlet.get("flow_rate", 0))  if outlet else 0.0,

        # ── Today's usage ──────────────────────────────────────
        "today_total_L":  round(today_total_L, 2),
        "daily_avg_L":    round(daily_avg_L, 2),
        "pct_of_daily_avg": pct_of_avg,

        # ── Valve ──────────────────────────────────────────────
        "valve_open":     bool(inlet.get("valve_open", True)) if inlet else True,

        # ── Leak ───────────────────────────────────────────────
        "leak_detected":  bool(inlet.get("leak_detected", False)) if inlet else False,
        "delta_L":        float(inlet.get("delta_L", 0)) if inlet else 0.0,

        # ── Device ─────────────────────────────────────────────
        "device_online":  online,
        "last_seen":      device["last_seen"].isoformat() if device and device.get("last_seen") else None,

        # ── Timestamp ──────────────────────────────────────────
        "ts": inlet["ts_ingested"].isoformat() if inlet else None,
    }


# ─────────────────────────────────────────────────────────────
#  HOME CHART — /analytics/daily
#  Powers the Monthly/Weekly/Daily toggle chart on Home screen
# ─────────────────────────────────────────────────────────────
@app.get("/analytics/daily", tags=["Home", "Analytics"])
def get_daily_analytics(
    user_id:   str,
    device_id: str,
    days:      int = Query(30, ge=1, le=90),
):
    """
    HOME SCREEN CHART — Returns daily water usage for last N days.
    Flutter filters this list by the selected tab (Daily=7, Weekly=28, Monthly=30).

    Response shape per day:
      date         — "YYYY-MM-DD"
      daily_usage_L — litres consumed that day
      avg_flow_rate — average L/min
      leak_events   — number of leak readings that day
    """
    since = _now() - timedelta(days=days)

    pipeline = [
        {"$match": {
            "user_id":   user_id,
            "device_id": device_id,
            "node":      "inlet",
            "ts_ingested": {"$gte": since},
        }},
        {"$group": {
            "_id": {
                "year":  {"$year":         "$ts_ingested"},
                "month": {"$month":        "$ts_ingested"},
                "day":   {"$dayOfMonth":   "$ts_ingested"},
            },
            "max_total_L":   {"$max": "$total_L"},
            "min_total_L":   {"$min": "$total_L"},
            "avg_flow":      {"$avg": "$flow_rate"},
            "leak_events":   {"$sum": {"$cond": [{"$eq": ["$leak_detected", True]}, 1, 0]}},
            "reading_count": {"$sum": 1},
        }},
        {"$project": {
            "_id": 0,
            "date": {"$dateFromParts": {
                "year":  "$_id.year",
                "month": "$_id.month",
                "day":   "$_id.day",
            }},
            "daily_usage_L":  {"$max": [{"$subtract": ["$max_total_L", "$min_total_L"]}, 0]},
            "avg_flow_rate":  {"$round": ["$avg_flow", 2]},
            "leak_events":    1,
            "reading_count":  1,
        }},
        {"$sort": {"date": 1}},
    ]

    results = list(readings_col.aggregate(pipeline))
    for r in results:
        if isinstance(r.get("date"), datetime):
            r["date"] = r["date"].strftime("%Y-%m-%d")
        r["daily_usage_L"] = round(r.get("daily_usage_L", 0), 2)

    return {
        "user_id":   user_id,
        "device_id": device_id,
        "days":      days,
        "count":     len(results),
        "data":      results,
    }


# ─────────────────────────────────────────────────────────────
#  LEAKAGES SCREEN — /leakages
#  Shows per-zone IN/OUT flow + valve toggle state
# ─────────────────────────────────────────────────────────────
@app.get("/leakages/{user_id}/{device_id}", tags=["Leakages"])
def get_leakages(user_id: str, device_id: str):
    """
    LEAKAGES SCREEN — Returns current inlet and outlet readings
    plus valve and leak status. Flutter uses this to show the
    IN/OUT gauges and the valve toggle colour state.

    Leak state colours (match UI):
      leak_detected=true  → red border  (Leak Detected)
      valve_open=false    → gold border (Valve Closed)
      normal              → blue border
    """
    inlet  = _get_latest_reading(user_id, device_id, "inlet")
    outlet = _get_latest_reading(user_id, device_id, "outlet")

    valve_open    = bool(inlet.get("valve_open",    True))  if inlet else True
    leak_detected = bool(inlet.get("leak_detected", False)) if inlet else False

    # Border/status state for UI colour logic
    if leak_detected:
        ui_state = "leak_detected"   # → red
    elif not valve_open:
        ui_state = "valve_closed"    # → gold/yellow
    else:
        ui_state = "normal"          # → blue/green

    return {
        "user_id":   user_id,
        "device_id": device_id,
        "ui_state":  ui_state,

        "inlet": {
            "flow_rate_lpm": float(inlet.get("flow_rate", 0)) if inlet else 0.0,
            "total_L":       float(inlet.get("total_L",   0)) if inlet else 0.0,
            "ts":            inlet["ts_ingested"].isoformat()  if inlet else None,
        },
        "outlet": {
            "flow_rate_lpm": float(outlet.get("flow_rate", 0)) if outlet else 0.0,
            "total_L":       float(outlet.get("total_L",   0)) if outlet else 0.0,
            "ts":            outlet["ts_ingested"].isoformat()  if outlet else None,
        },

        "valve_open":    valve_open,
        "leak_detected": leak_detected,
        "delta_L":       float(inlet.get("delta_L", 0)) if inlet else 0.0,
    }


# ─── Valve command ───────────────────────────────────────────
class ValveCommandBody(BaseModel):
    user_id:   str
    device_id: str
    cmd:       str          # "open" | "close"
    override:  bool = False # Force open even during active leak


@app.post("/valve/command", tags=["Leakages"])
def send_valve_command(body: ValveCommandBody):
    """
    LEAKAGES SCREEN — Send open/close command to valve.
    Flutter calls this when user toggles the valve switch.
    Requires override=true to open valve while leak is active.
    Always show a confirmation dialog in the app before calling this.
    """
    if body.cmd not in ("open", "close"):
        raise HTTPException(status_code=400, detail="cmd must be 'open' or 'close'")

    success = publish_valve_command(
        user_id=body.user_id,
        device_id=body.device_id,
        cmd=body.cmd,
        reason="app_user_command",
        override=body.override,
    )

    if not success:
        raise HTTPException(
            status_code=503,
            detail="MQTT broker not connected — command not sent"
        )

    return {
        "status":    "command_sent",
        "cmd":       body.cmd,
        "device_id": body.device_id,
        "ts":        _now().isoformat(),
    }


@app.get("/valve/logs/{user_id}/{device_id}", tags=["Leakages"])
def get_valve_logs(
    user_id:   str,
    device_id: str,
    limit:     int = Query(20, ge=1, le=100),
):
    """
    LEAKAGES SCREEN — Recent valve open/close history.
    Shows who closed the valve and why (user vs leak detection).
    """
    docs = list(
        valve_log_col.find(
            {"user_id": user_id, "device_id": device_id},
            {"_id": 0}
        )
        .sort("ts", -1)
        .limit(limit)
    )
    for d in docs:
        if isinstance(d.get("ts"), datetime):
            d["ts"] = d["ts"].isoformat()
    return {"count": len(docs), "items": docs}


# ─────────────────────────────────────────────────────────────
#  REPORT SCREEN — /report/monthly
#  Shows: Monthly Water Usage, Weekly Average, Daily Average,
#         Leaks Detected — with year/month dropdown selector
# ─────────────────────────────────────────────────────────────
@app.get("/report/monthly", tags=["Report"])
def get_monthly_report(
    user_id:   str,
    device_id: str,
    year:      int = Query(..., ge=2020, le=2100),
    month:     int = Query(..., ge=1,    le=12),
):
    """
    REPORT SCREEN — Full monthly summary for the selected year/month.
    Flutter populates this when user changes the year/month dropdowns.

    Response fields map directly to Report screen cards:
      total_usage_L   → "Monthly Water Usage: X,XXX Litres"
      weekly_avg_L    → "Weekly Average: X,XXX Litres"
      daily_avg_L     → "Daily Average: XXX Litres"
      leaks_detected  → "Leaks Detected: N"
    """
    # First and last day of the requested month
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    pipeline = [
        {"$match": {
            "user_id":   user_id,
            "device_id": device_id,
            "node":      "inlet",
            "ts_ingested": {"$gte": month_start, "$lt": month_end},
        }},
        {"$group": {
            "_id": {
                "year":  {"$year":       "$ts_ingested"},
                "month": {"$month":      "$ts_ingested"},
                "day":   {"$dayOfMonth": "$ts_ingested"},
            },
            "max_L":       {"$max": "$total_L"},
            "min_L":       {"$min": "$total_L"},
            "leak_events": {"$sum": {"$cond": [{"$eq": ["$leak_detected", True]}, 1, 0]}},
        }},
        {"$project": {
            "_id":        0,
            "day_usage":  {"$max": [{"$subtract": ["$max_L", "$min_L"]}, 0]},
            "leak_events": 1,
        }},
    ]

    days_data = list(readings_col.aggregate(pipeline))
    days_count = len(days_data) or 1  # avoid division by zero

    total_usage_L  = sum(d["day_usage"]   for d in days_data)
    total_leaks    = sum(d["leak_events"] for d in days_data)
    daily_avg_L    = total_usage_L / days_count
    weekly_avg_L   = total_usage_L / max(days_count / 7, 1)

    # Also count distinct leak alert documents for the month
    alert_count = alerts_col.count_documents({
        "user_id":    user_id,
        "device_id":  device_id,
        "ts_created": {"$gte": month_start, "$lt": month_end},
    })

    return {
        "user_id":       user_id,
        "device_id":     device_id,
        "year":          year,
        "month":         month,
        "days_with_data": days_count,

        # ── Report screen cards ────────────────────────────────
        "total_usage_L":  round(total_usage_L, 2),
        "weekly_avg_L":   round(weekly_avg_L,  2),
        "daily_avg_L":    round(daily_avg_L,   2),
        "leaks_detected": alert_count,
    }


# ─────────────────────────────────────────────────────────────
#  ALERTS / NOTIFICATION BELL — /alerts
#  Powers the bell badge count + alert list screen
# ─────────────────────────────────────────────────────────────
@app.get("/alerts/{user_id}", tags=["Alerts"])
def get_alerts(
    user_id:   str,
    device_id: Optional[str] = Query(None),
    resolved:  bool          = Query(False),
):
    """
    ALERTS SCREEN — List leak alerts.
    - resolved=false (default) → open alerts → bell badge count
    - resolved=true            → history of past leaks

    Response fields:
      id           — use this to call /alerts/{id}/resolve
      type         — "leak_detected"
      delta_L      — volume difference that triggered the alert
      source       — "device" | "backend" | "both"
      ts_created   — when the leak was detected
      ts_resolved  — when it was resolved (null if still open)
    """
    query: dict = {"user_id": user_id, "resolved": resolved}
    if device_id:
        query["device_id"] = device_id

    docs = list(
        alerts_col.find(query)
        .sort("ts_created", -1)
        .limit(100)
    )
    result = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        if isinstance(d.get("ts_created"),  datetime): d["ts_created"]  = d["ts_created"].isoformat()
        if isinstance(d.get("ts_resolved"), datetime): d["ts_resolved"] = d["ts_resolved"].isoformat()
        result.append(d)

    return {"count": len(result), "items": result}


@app.get("/alerts/{user_id}/count", tags=["Alerts"])
def get_alert_count(user_id: str):
    """
    NOTIFICATION BELL BADGE — Returns just the unread count.
    Flutter polls this to update the red badge number.
    """
    count = alerts_col.count_documents({"user_id": user_id, "resolved": False})
    return {"user_id": user_id, "unread_count": count}


@app.post("/alerts/{alert_id}/resolve", tags=["Alerts"])
def resolve_alert(alert_id: str):
    """
    ALERTS SCREEN — Mark a specific leak alert as resolved.
    Call this BEFORE sending a valve open command so the ESP32
    doesn't reject the open due to an active leak flag.
    """
    try:
        oid = ObjectId(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    result = alerts_col.update_one(
        {"_id": oid, "resolved": False},
        {"$set": {"resolved": True, "ts_resolved": _now()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found or already resolved")

    return {"status": "resolved", "alert_id": alert_id, "ts": _now().isoformat()}


# ─────────────────────────────────────────────────────────────
#  DEVICES — /devices
#  Shows device online/offline status (used on Home + Settings)
# ─────────────────────────────────────────────────────────────
@app.get("/devices/{user_id}", tags=["Devices"])
def get_devices(user_id: str):
    """
    HOME + SETTINGS — List all registered devices for a user.
    online=true  if heartbeat received within last 90 seconds.
    online=false if device is silent (disconnected/offline).
    Flutter uses this to show the offline banner on the Home screen.
    """
    docs  = list(devices_col.find({"user_id": user_id}, {"_id": 0}))
    now   = _now()

    for d in docs:
        last_seen = d.get("last_seen")
        d["online"] = bool(last_seen and (now - last_seen).total_seconds() < 90)
        if isinstance(last_seen, datetime):
            d["last_seen"] = last_seen.isoformat()

    return {"user_id": user_id, "count": len(docs), "devices": docs}


# ─────────────────────────────────────────────────────────────
#  RAW READINGS — /latest  (kept from original for debugging)
# ─────────────────────────────────────────────────────────────
@app.get("/latest", tags=["Debug"])
def latest(
    limit:     int           = Query(10, ge=1, le=200),
    user_id:   Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    node:      Optional[str] = Query(None),
):
    """
    DEBUG — Raw readings from MongoDB. Useful for verifying
    that MQTT data is arriving and being stored correctly.
    Not intended for production frontend use.
    """
    query = {}
    if user_id:   query["user_id"]   = user_id
    if device_id: query["device_id"] = device_id
    if node:      query["node"]      = node

    docs = list(
        readings_col.find(query, {"_id": 0})
        .sort("ts_ingested", -1)
        .limit(limit)
    )
    for d in docs:
        if isinstance(d.get("ts_ingested"), datetime):
            d["ts_ingested"] = d["ts_ingested"].isoformat()

    return {"count": len(docs), "items": docs}
