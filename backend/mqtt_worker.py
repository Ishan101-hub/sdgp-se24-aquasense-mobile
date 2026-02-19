import os
import json
import ssl
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from db import readings_col, events_col

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

TOPIC_INLET = os.getenv("TOPIC_INLET", "home/waterflow/sensor1/#")
TOPIC_OUTLET = os.getenv("TOPIC_OUTLET", "home/waterflow/sensor2/#")
TOPIC_VALVE = os.getenv("TOPIC_VALVE", "home/waterflow/valve/#")
TOPIC_LEAK = os.getenv("TOPIC_LEAK", "home/waterflow/leak/#")

if not MQTT_HOST or not MQTT_USERNAME or not MQTT_PASSWORD:
    raise RuntimeError("MQTT_HOST / MQTT_USERNAME / MQTT_PASSWORD missing in .env")

_client = None


def _now_utc():
    return datetime.now(timezone.utc)


def on_connect(client, userdata, flags, rc, properties=None):
    events_col.insert_one({"type": "mqtt_connect", "rc": rc, "ts": _now_utc()})

    if rc == 0:
        client.subscribe([(TOPIC_INLET, 1), (TOPIC_OUTLET, 1), (TOPIC_VALVE, 1), (TOPIC_LEAK, 1)])
        events_col.insert_one(
            {"type": "mqtt_subscribed", "topics": [TOPIC_INLET, TOPIC_OUTLET, TOPIC_VALVE, TOPIC_LEAK], "ts": _now_utc()}
            )


def parse_payload(raw: str):
    raw = raw.strip()

    # Try numeric (flow rate, total_L)
    try:
        return {"value": float(raw), "raw": raw}
    except ValueError:
        pass

    # Try JSON (if later you send JSON from ESP32 / other services)
    try:
        return {"json": json.loads(raw), "raw": raw}
    except Exception:
        pass

    # Fallback string (valve status, leak alerts)
    return {"value": raw, "raw": raw}


def on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    data = parse_payload(raw)

    print(f"Received {msg.topic} -> {raw}")   # <-- add this

    readings_col.insert_one({
        "topic": msg.topic,
        "qos": msg.qos,
        "ts_ingested": _now_utc(),
        "data": data,
    })


def on_disconnect(client, userdata, rc, properties=None):
    events_col.insert_one({"type": "mqtt_disconnect", "rc": rc, "ts": _now_utc()})


def start_mqtt():
    """Start MQTT loop in background (non-blocking)."""
    global _client
    if _client is not None:
        return

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.tls_insecure_set(False)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    _client = client


def stop_mqtt():
    """Stop MQTT loop."""
    global _client
    if _client is None:
        return
    try:
        _client.loop_stop()
        _client.disconnect()
    finally:
        _client = None
