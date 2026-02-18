import ssl
from datetime import datetime, timezone

import paho.mqtt.client as paho
from paho import mqtt
from pymongo import MongoClient


# -------------------- MongoDB --------------------
mongo_client = MongoClient("mongodb://localhost:27017/") # for mongo atlas: "mongodb+srv://<user>:<password>@aquasense.kk3xa33.mongodb.net/?retryWrites=true&w=majority"
db = mongo_client["waterflow_db"]
readings_col = db["sensor_readings"]   # numeric readings
events_col = db["events"]              # valve/leak/status messages


# -------------------- HiveMQ Cloud --------------------
HIVEMQ_HOST = "66791e6741b44aecb122ab7b59807177.s1.eu.hivemq.cloud"
HIVEMQ_PORT = 8883
HIVEMQ_USERNAME = "AquaSense"
HIVEMQ_PASSWORD = "Aquasense@123@#"

TOPIC_SUB = "home/waterflow/#"


def now_utc():
    return datetime.now(timezone.utc)


def on_connect(client, userdata, flags, reasonCode, properties):
    # reasonCode is a ReasonCodes object in MQTTv5
    if getattr(reasonCode, "value", reasonCode) == 0:
        print("✅ Connected to HiveMQ Cloud")
        client.subscribe(TOPIC_SUB, qos=1)
        print(f"✅ Subscribed to {TOPIC_SUB}")
    else:
        print(f"❌ Connection failed. reasonCode={reasonCode} (value={getattr(reasonCode,'value',None)})")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode(errors="ignore").strip()
    ts = now_utc()

    print(f"Received: {topic} -> {payload}")

    try:
        # Numeric topics
        if topic.endswith("/flow_rate") or topic.endswith("/total_L"):
            value = float(payload)

            doc = {
                "topic": topic,
                "value": value,
                "timestamp": ts,
            }

            parts = topic.split("/")  # home/waterflow/sensor1/flow_rate
            if len(parts) >= 4:
                doc["sensorId"] = parts[2]   # sensor1 / sensor2
                doc["metric"] = parts[3]     # flow_rate / total_L

            readings_col.insert_one(doc)
            print("✅ Saved reading")

        else:
            # Status/event topics like Opened/Closed/Leak Detected/Normal
            doc = {
                "topic": topic,
                "message": payload,
                "timestamp": ts,
            }
            events_col.insert_one(doc)
            print("✅ Saved event/status")

    except Exception as e:
        print("❌ Error handling message:", e)


# -------------------- MQTT Client --------------------
client = paho.Client(client_id="PythonBackend", protocol=paho.MQTTv5)

client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
client.tls_insecure_set(False)

client.username_pw_set(HIVEMQ_USERNAME, HIVEMQ_PASSWORD)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to HiveMQ Cloud...")
client.connect(HIVEMQ_HOST, HIVEMQ_PORT, keepalive=60)

print("Starting MQTT client...")
client.loop_forever()
