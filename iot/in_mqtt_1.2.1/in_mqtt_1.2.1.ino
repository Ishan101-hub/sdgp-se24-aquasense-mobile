#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// -------------------- Pins --------------------
#define SENSOR    26
#define RELAY_PIN 22
#define LED_BUILTIN 2

// -------------------- Wi-Fi Configuration --------------------
#define WIFI_SSID     "Dialog 4G 780"
#define WIFI_PASSWORD "40De7e62"

// -------------------- MQTT / HiveMQ Configuration --------------------
const char* mqtt_server   = "66791e6741b44aecb122ab7b59807177.s1.eu.hivemq.cloud";
const char* mqtt_username = "AquaSense";
const char* mqtt_password = "Aquasense@123@#";
const int   mqtt_port     = 8883;

// ==================== MQTT Topics ====================
// Structure: aquasense/{network_id}/{zone_id}/{device_id}/...
// This makes topics fully scalable — swap out home_01/bathroom_01/pipe_01
// to support multiple buildings, rooms, and monitoring nodes from one backend.
//
// Your backend developer can subscribe using wildcards, e.g.:
//   aquasense/+/+/+/sensor/inlet/flow_rate  ← all inlet sensors across all devices
//   aquasense/home_01/#                  ← everything in home_01
// =====================================================

#define NETWORK_ID  "home_01"
#define ZONE_ID     "bathroom_01"
#define DEVICE_ID   "pipe_01"

#define BASE        "aquasense/" NETWORK_ID "/" ZONE_ID "/" DEVICE_ID

// Sensor data
#define TOPIC_INLET_FLOW        BASE "/sensor/inlet/flow_rate"
#define TOPIC_INLET_FLOW_LIVE   BASE "/sensor/inlet/live_flow"
#define TOPIC_INLET_TOTAL       BASE "/sensor/inlet/total_L"
#define TOPIC_OUTLET_FLOW       BASE "/sensor/outlet/flow_rate"
#define TOPIC_OUTLET_TOTAL      BASE "/sensor/outlet/total_L"
#define TOPIC_OUTLET_HEARTBEAT  BASE "/sensor/outlet/heartbeat"

// Valve control
#define TOPIC_VALVE_COMMAND     BASE "/valve/command"
#define TOPIC_VALVE_STATUS      BASE "/valve/status"

// Leak alert
#define TOPIC_LEAK_ALERT        BASE "/leak/alert"

// -------------------- Root CA Certificate (ISRG Root X1) --------------------
static const char *root_ca PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
)EOF";

// -------------------- MQTT & WiFi Clients --------------------
WiFiClientSecure espClient;
PubSubClient     client(espClient);

// -------------------- Flow Variables --------------------
volatile byte  pulseCount      = 0;
byte           pulse1Sec       = 0;
float          flowRateInlet   = 0.0;
unsigned int   flowMilliLitres = 0;
unsigned long  totalMilliLitres = 0;
float          flowRateOutlet  = 0.0;
unsigned long  totalOutletML   = 0;
long           previousMillis  = 0;
int            interval        = 1000;
float          calibrationFactor = 6.5;

// -------------------- Valve & Leak Detection --------------------
bool valveState      = true;   // true = open
bool leakDetected    = false;  // Once true, stays true until manual reset via app
int  leakConfirmCount = 0;
const int LEAK_CONFIRM_THRESHOLD = 3;  // Must detect leak for 3 consecutive seconds

// -------------------- Heartbeat Watchdog --------------------
unsigned long lastHeartbeatMillis        = 0;
const unsigned long HEARTBEAT_TIMEOUT_MS = 5000;  // 5 seconds

// -------------------- Leak Threshold --------------------
const float leakThreshold = 0.8;  // L/min difference to flag as leak

// -------------------- ISR --------------------
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

// ==================== MQTT CALLBACK ====================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("MQTT IN [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // ── Valve commands from Flutter mobile app ──────────────────────────────
  if (String(topic) == TOPIC_VALVE_COMMAND) {
    if (message == "open") {
      // Manual "open" from app is the ONLY way to reopen valve after a leak
      leakDetected     = false;
      leakConfirmCount = 0;
      openValve();
      client.publish(TOPIC_VALVE_STATUS, "Opened", true);
      client.publish(TOPIC_LEAK_ALERT,   "Normal", true);
    } else if (message == "close") {
      closeValve();
      client.publish(TOPIC_VALVE_STATUS, "Closed", true);
    }
  }

  // ── Outlet flow data from second ESP32 ──────────────────────────────────
  if (String(topic) == TOPIC_OUTLET_FLOW) {
    flowRateOutlet = message.toFloat();
  }
  if (String(topic) == TOPIC_OUTLET_TOTAL) {
    totalOutletML = message.toFloat() * 1000;  // L → mL
  }

  // ── Heartbeat from outlet ESP32 ─────────────────────────────────────────
  if (String(topic) == TOPIC_OUTLET_HEARTBEAT) {
    lastHeartbeatMillis = millis();
  }
}

// ==================== MQTT RECONNECT ====================
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");

    String clientId = "ESP32-Inlet-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("✅ MQTT Connected");

      client.subscribe(TOPIC_VALVE_COMMAND);
      client.subscribe(TOPIC_OUTLET_FLOW);
      client.subscribe(TOPIC_OUTLET_TOTAL);
      client.subscribe(TOPIC_OUTLET_HEARTBEAT);

      // Publish actual valve state on reconnect (not hardcoded "Opened")
      client.publish(TOPIC_VALVE_STATUS, valveState ? "Opened" : "Closed", true);

      // Republish current leak state so app re-syncs
      if (leakDetected) {
        client.publish(TOPIC_LEAK_ALERT,
          "{\"status\":\"LEAK_DETECTED\",\"valve\":\"CLOSED\",\"note\":\"reconnected\"}",
          true
        );
      } else {
        client.publish(TOPIC_LEAK_ALERT, "Normal", true);
      }

    } else {
      Serial.print("❌ Failed, rc=");
      Serial.print(client.state());
      Serial.println(" — retrying in 5s");
      delay(5000);
    }
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  pinMode(SENSOR, INPUT_PULLUP);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);   // Energise relay → NC valve opens
  pinMode(LED_BUILTIN, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected — IP: " + WiFi.localIP().toString());

  espClient.setCACert(root_ca);
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setKeepAlive(60);
  client.setSocketTimeout(30);
  client.setBufferSize(512);

  // Initialise heartbeat timer so watchdog doesn't trigger immediately on boot
  lastHeartbeatMillis = millis();

  Serial.println("✅ Setup complete — AquaSense Inlet Device Ready");
  Serial.println("📡 Publishing to: " BASE);
}

// ==================== MAIN LOOP ====================
void loop() {
  if (!client.connected()) reconnectMQTT();
  client.loop();

  long currentMillis = millis();

  if (currentMillis - previousMillis > interval) {
    pulse1Sec  = pulseCount;
    pulseCount = 0;
    previousMillis = currentMillis;

    flowRateInlet    = ((1000.0 / interval) * pulse1Sec) / calibrationFactor;
    flowMilliLitres  = (flowRateInlet / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    // ── Heartbeat watchdog ──────────────────────────────────────────────────
    bool outletAlive = (millis() - lastHeartbeatMillis) < HEARTBEAT_TIMEOUT_MS;

    // ── Leak detection ──────────────────────────────────────────────────────
    if (outletAlive) {
      if (!leakDetected) {
        float flowDiff = flowRateInlet - flowRateOutlet;

        if (flowDiff > leakThreshold) {
          leakConfirmCount++;
          Serial.print("⚠️  Leak suspicion count: ");
          Serial.println(leakConfirmCount);

          if (leakConfirmCount >= LEAK_CONFIRM_THRESHOLD) {
            leakDetected     = true;
            leakConfirmCount = 0;
            closeValve();

            // Publish full JSON context of the leak event
            char leakPayload[160];
            snprintf(leakPayload, sizeof(leakPayload),
              "{\"status\":\"LEAK_DETECTED\","
              "\"valve\":\"CLOSED\","
              "\"inlet_flow\":%.2f,"
              "\"outlet_flow\":%.2f,"
              "\"diff\":%.2f,"
              "\"threshold\":%.2f}",
              flowRateInlet,
              flowRateOutlet,
              flowDiff,
              leakThreshold
            );

            client.publish(TOPIC_LEAK_ALERT,   leakPayload, true);
            client.publish(TOPIC_VALVE_STATUS, "Closed",    true);
            Serial.println("🚨 LEAK CONFIRMED — Valve closed permanently until manual reset.");
          }
        } else {
          leakConfirmCount = 0;
        }
      }
      // leakDetected == true: valve stays closed, do nothing until app sends "open"

    } else {
      leakConfirmCount = 0;
      Serial.println("⚠️  Outlet heartbeat timeout — leak detection suppressed.");
    }

    // ── Publish inlet data ──────────────────────────────────────────────────
    char flowRateStr[16];
    char totalLStr[16];

    dtostrf(flowRateInlet,             6, 2, flowRateStr);
    dtostrf(totalMilliLitres / 1000.0, 6, 2, totalLStr);

    client.publish(TOPIC_INLET_FLOW,      flowRateStr);
    client.publish(TOPIC_INLET_FLOW_LIVE, flowRateStr);
    client.publish(TOPIC_INLET_TOTAL,     totalLStr);

    // ── Serial monitor ──────────────────────────────────────────────────────
    Serial.println("────────────────────────────────────────────────");
    Serial.print("  INLET  → "); Serial.print(flowRateInlet, 2);
    Serial.print(" L/min | Total: "); Serial.print(totalMilliLitres / 1000.0, 2); Serial.println(" L");
    Serial.print("  OUTLET → "); Serial.print(flowRateOutlet, 2);
    Serial.print(" L/min | Total: "); Serial.print(totalOutletML / 1000.0, 2); Serial.println(" L");
    Serial.print("  DIFF   → "); Serial.print(flowRateInlet - flowRateOutlet, 2); Serial.println(" L/min");
    Serial.print("  VALVE  → "); Serial.println(valveState    ? "OPEN ✅"        : "CLOSED 🚨");
    Serial.print("  LEAK   → "); Serial.println(leakDetected  ? "DETECTED 🚨"    : "None ✅");
    Serial.print("  OUTLET → "); Serial.println(outletAlive   ? "Online ✅"      : "OFFLINE ⚠️");
    Serial.println("────────────────────────────────────────────────");
  }
}

// ==================== VALVE CONTROL ====================
void openValve() {
  valveState = true;
  digitalWrite(RELAY_PIN, HIGH);   // Energise relay → NC valve opens
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("✅ Valve Opened");
}

void closeValve() {
  valveState = false;
  digitalWrite(RELAY_PIN, LOW);    // De-energise relay → NC valve closes
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("🚨 Valve Closed");
}
