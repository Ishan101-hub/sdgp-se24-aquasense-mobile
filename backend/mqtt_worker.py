# mqtt_worker.py
# Subscribes to all AquaSense MQTT topics, parses incoming JSON
# payloads from the ESP32 firmware, stores structured documents,
# and runs backend-side leak detection as a safety net.

import os
import json
import ssl
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from db import readings_col, events_col, alerts_col, valve_log_col, devices_col

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_USERNAME")
MQTT_PASS = os.getenv("MQTT_PASSWORD")

# Topic base — subscribes to all users/devices with wildcard
# Matches: aquasense/{user_id}/{device_id}/...
TOPIC_BASE = os.getenv("TOPIC_BASE", "aquasense/+/+")

LEAK_THRESHOLD_L   = float(os.getenv("LEAK_VOLUME_THRESHOLD_L", "5.0"))
LEAK_CONFIRM_COUNT = int(os.getenv("LEAK_CONFIRM_READINGS", "3"))
VALVE_CMD_TOKEN    = os.getenv("VALVE_CMD_TOKEN", "")

if not all([MQTT_HOST, MQTT_USER, MQTT_PASS]):
    raise RuntimeError("MQTT credentials missing in .env")

_client = None

# In-memory state for backend leak detection
# { "user_id:device_id": {"inlet_L": float, "outlet_L": float, "over_count": int} }
_device_state: dict = {}


def _now():
    return datetime.now(timezone.utc)


def _parse_topic(topic: str) -> dict | None:
    """
    Parse: aquasense/{user_id}/{device_id}/{node}/{subtopic}
    Returns None if topic doesn't match expected structure.
    """
    parts = topic.split("/")
    if len(parts) < 5 or parts[0] != "aquasense":
        return None
    return {
        "user_id":   parts[1],
        "device_id": parts[2],
        "node":      parts[3],    # inlet | outlet | valve | leak
        "subtopic":  parts[4],    # data | status | heartbeat | alert | command
        "key":       f"{parts[1]}:{parts[2]}",
    }


def _get_state(key: str) -> dict:
    if key not in _device_state:
        _device_state[key] = {"inlet_L": 0.0, "outlet_L": 0.0, "over_count": 0}
    return _device_state[key]


# ─── Handlers ────────────────────────────────────────────────

def _handle_flow_data(parsed: dict, data: dict, topic: str):
    """Store inlet or outlet reading and run backend leak detection."""
    node = parsed["node"]

    readings_col.insert_one({
        "user_id":       parsed["user_id"],
        "device_id":     parsed["device_id"],
        "node":          node,
        "flow_rate":     float(data.get("flow_rate", 0)),
        "total_L":       float(data.get("total_L", 0)),
        "valve_open":    data.get("valve_open"),      # inlet only
        "leak_detected": data.get("leak_detected"),   # inlet only
        "delta_L":       data.get("delta_L"),         # inlet only
        "rssi":          data.get("rssi"),
        "uptime_s":      data.get("uptime_s"),
        "ts_ingested":   _now(),
        "topic":         topic,
    })

    # Update in-memory totals for backend leak check
    state = _get_state(parsed["key"])
    if node == "inlet":
        state["inlet_L"]  = float(data.get("total_L", 0))
    elif node == "outlet":
        state["outlet_L"] = float(data.get("total_L", 0))

    _check_leak_backend(parsed["user_id"], parsed["device_id"], parsed["key"], state)
    print(f"[{node.upper()}] {parsed['device_id']} flow={data.get('flow_rate')} L/min total={data.get('total_L')} L")


def _check_leak_backend(user_id: str, device_id: str, key: str, state: dict):
    """
    Backend-side leak detection using cumulative volume delta.
    Independent of ESP32 — catches anything the device may miss.
    Creates an alert and sends a valve close command when confirmed.
    """
    delta = state["inlet_L"] - state["outlet_L"]

    if delta > LEAK_THRESHOLD_L:
        state["over_count"] += 1
    else:
        state["over_count"] = 0
        return

    if state["over_count"] < LEAK_CONFIRM_COUNT:
        return

    # Already have an open alert? Don't duplicate.
    existing = alerts_col.find_one({"user_id": user_id, "device_id": device_id, "resolved": False})
    if existing:
        return

    alerts_col.insert_one({
        "user_id":     user_id,
        "device_id":   device_id,
        "type":        "leak_detected",
        "inlet_L":     state["inlet_L"],
        "outlet_L":    state["outlet_L"],
        "delta_L":     delta,
        "resolved":    False,
        "ts_created":  _now(),
        "ts_resolved": None,
        "source":      "backend",
    })

    print(f"[LEAK] Backend confirmed: {device_id} delta={delta:.2f}L — closing valve")
    _publish_valve_command(user_id, device_id, "close", reason="backend_leak_detection")


def _handle_valve_status(parsed: dict, data: dict):
    """Log valve state change reported by device."""
    valve_log_col.insert_one({
        "user_id":     parsed["user_id"],
        "device_id":   parsed["device_id"],
        "state":       data.get("state"),
        "leak_active": data.get("leak_active"),
        "ts":          _now(),
        "source":      "device_report",
    })
    print(f"[VALVE] {parsed['device_id']} state={data.get('state')}")


def _handle_leak_alert(parsed: dict, data: dict):
    """Handle device-reported leak alert or resolution."""
    user_id   = parsed["user_id"]
    device_id = parsed["device_id"]
    status    = data.get("status", "")

    if status == "leak_detected":
        existing = alerts_col.find_one({"user_id": user_id, "device_id": device_id, "resolved": False})
        if existing:
            alerts_col.update_one({"_id": existing["_id"]}, {"$set": {"source": "both"}})
        else:
            alerts_col.insert_one({
                "user_id":     user_id,
                "device_id":   device_id,
                "type":        "leak_detected",
                "inlet_L":     data.get("inlet_L"),
                "outlet_L":    data.get("outlet_L"),
                "delta_L":     data.get("delta_L"),
                "resolved":    False,
                "ts_created":  _now(),
                "ts_resolved": None,
                "source":      "device",
            })
        print(f"[LEAK ALERT] {device_id} device-reported delta={data.get('delta_L')}L")

    elif status == "normal":
        alerts_col.update_many(
            {"user_id": user_id, "device_id": device_id, "resolved": False},
            {"$set": {"resolved": True, "ts_resolved": _now()}}
        )
        print(f"[LEAK ALERT] {device_id} resolved")


def _handle_heartbeat(parsed: dict, raw: str):
    """Update device last-seen. Used by /devices endpoint for online status."""
    devices_col.update_one(
        {"user_id": parsed["user_id"], "device_id": parsed["device_id"], "node": parsed["node"]},
        {"$set": {
            "last_seen": _now(),
            "uptime_s":  int(raw) if raw.isdigit() else None,
            "status":    "online",
        }},
        upsert=True
    )


def _handle_node_status(parsed: dict, raw: str):
    """Handle LWT online/offline status from device."""
    status = raw.strip().lower()
    devices_col.update_one(
        {"user_id": parsed["user_id"], "device_id": parsed["device_id"], "node": parsed["node"]},
        {"$set": {"status": status, "last_seen": _now() if status == "online" else None}},
        upsert=True
    )
    events_col.insert_one({
        "type":      f"device_{status}",
        "user_id":   parsed["user_id"],
        "device_id": parsed["device_id"],
        "node":      parsed["node"],
        "ts":        _now(),
    })
    print(f"[STATUS] {parsed['node']} {parsed['device_id']} → {status}")


# ─── Valve command publisher ─────────────────────────────────

def _publish_valve_command(user_id: str, device_id: str, cmd: str,
                            reason: str = "api_request", override: bool = False) -> bool:
    """Publish authenticated valve command. Used internally + by REST API."""
    global _client
    if _client is None or not _client.is_connected():
        print(f"[VALVE CMD] MQTT not connected — cannot send {cmd}")
        return False

    topic   = f"aquasense/{user_id}/{device_id}/valve/command"
    payload = json.dumps({"cmd": cmd, "token": VALVE_CMD_TOKEN, "override": override, "reason": reason})
    result  = _client.publish(topic, payload, qos=1, retain=False)

    valve_log_col.insert_one({
        "user_id":   user_id,
        "device_id": device_id,
        "command":   cmd,
        "reason":    reason,
        "override":  override,
        "ts":        _now(),
        "source":    "backend",
    })

    print(f"[VALVE CMD] → {topic} cmd={cmd} reason={reason}")
    return result.rc == mqtt.MQTT_ERR_SUCCESS


# ─── MQTT Callbacks ──────────────────────────────────────────

def on_connect(client, userdata, flags, rc, properties=None):
    events_col.insert_one({"type": "mqtt_connect", "rc": rc, "ts": _now()})
    if rc == 0:
        topics = [
            (f"{TOPIC_BASE}/inlet/data",      1),
            (f"{TOPIC_BASE}/inlet/status",    1),
            (f"{TOPIC_BASE}/inlet/heartbeat", 1),
            (f"{TOPIC_BASE}/outlet/data",     1),
            (f"{TOPIC_BASE}/outlet/status",   1),
            (f"{TOPIC_BASE}/outlet/heartbeat",1),
            (f"{TOPIC_BASE}/valve/status",    1),
            (f"{TOPIC_BASE}/leak/alert",      1),
        ]
        client.subscribe(topics)
        print(f"[MQTT] ✅ Connected — subscribed to {len(topics)} topics")
    else:
        print(f"[MQTT] ❌ Connection failed rc={rc}")


def on_message(client, userdata, msg):
    raw    = msg.payload.decode("utf-8", errors="replace").strip()
    topic  = msg.topic
    parsed = _parse_topic(topic)

    if not parsed:
        print(f"[MQTT] Unknown topic: {topic}")
        return

    node, subtopic = parsed["node"], parsed["subtopic"]

    if subtopic == "data" and node in ("inlet", "outlet"):
        try:
            data = json.loads(raw)
            _handle_flow_data(parsed, data, topic)
        except json.JSONDecodeError:
            print(f"[MQTT] Bad JSON on {topic}: {raw}")

    elif subtopic == "status":
        if raw in ("online", "offline"):
            _handle_node_status(parsed, raw)
        elif node == "valve":
            try:
                _handle_valve_status(parsed, json.loads(raw))
            except json.JSONDecodeError:
                pass

    elif subtopic == "heartbeat":
        _handle_heartbeat(parsed, raw)

    elif subtopic == "alert" and node == "leak":
        try:
            _handle_leak_alert(parsed, json.loads(raw))
        except json.JSONDecodeError:
            pass


def on_disconnect(client, userdata, rc, properties=None):
    events_col.insert_one({"type": "mqtt_disconnect", "rc": rc, "ts": _now()})
    print(f"[MQTT] Disconnected rc={rc}")


# ─── Start / Stop ────────────────────────────────────────────

def start_mqtt():
    global _client
    if _client is not None:
        return

    c = mqtt.Client(client_id="AquaSense-Backend", protocol=mqtt.MQTTv311)
    c.username_pw_set(MQTT_USER, MQTT_PASS)
    c.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    c.tls_insecure_set(False)
    c.on_connect    = on_connect
    c.on_message    = on_message
    c.on_disconnect = on_disconnect
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    c.loop_start()
    _client = c
    print("[MQTT] Worker started")


def stop_mqtt():
    global _client
    if _client is None:
        return
    try:
        _client.loop_stop()
        _client.disconnect()
        print("[MQTT] Worker stopped")
    finally:
        _client = None


def get_mqtt_client():
    return _client


def publish_valve_command(user_id: str, device_id: str, cmd: str,
                           reason: str = "api_request", override: bool = False) -> bool:
    """Public wrapper — called by REST API endpoints."""
    return _publish_valve_command(user_id, device_id, cmd, reason, override)
