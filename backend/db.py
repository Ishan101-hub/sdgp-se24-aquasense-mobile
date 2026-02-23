# db.py
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB  = os.getenv("MONGODB_DB", "aquasense")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI missing in .env")

client = MongoClient(MONGODB_URI)
db     = client[MONGODB_DB]

# ─── Collections ─────────────────────────────────────────────
readings_col  = db["readings"]    # Inlet / Outlet flow readings (from MQTT)
events_col    = db["events"]      # MQTT connect/disconnect logs
alerts_col    = db["alerts"]      # Leak detections
valve_log_col = db["valve_logs"]  # Every valve open/close command
devices_col   = db["devices"]     # Device online/offline heartbeat state

# ─── Indexes (safe to call multiple times) ───────────────────
def ensure_indexes():
    # Fast queries: latest readings per device+node
    readings_col.create_index(
        [("user_id", ASCENDING), ("device_id", ASCENDING), ("ts_ingested", DESCENDING)]
    )
    readings_col.create_index([("ts_ingested", DESCENDING)])

    # TTL: auto-delete raw readings older than 90 days
    readings_col.create_index(
        [("ts_ingested", ASCENDING)],
        expireAfterSeconds=90 * 24 * 3600,
        name="ttl_90days"
    )

    # Alerts: find open alerts fast
    alerts_col.create_index(
        [("user_id", ASCENDING), ("device_id", ASCENDING), ("resolved", ASCENDING)]
    )

    # Devices: lookup by user
    devices_col.create_index([("user_id", ASCENDING)])

    # Valve log: chronological per device
    valve_log_col.create_index(
        [("user_id", ASCENDING), ("device_id", ASCENDING), ("ts", DESCENDING)]
    )
