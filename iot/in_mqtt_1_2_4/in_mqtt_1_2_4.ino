//---------------INLET — with SoftAP Provisioning----------------

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ArduinoJson.h>

// -------------------- Pins --------------------
#define SENSOR      26
#define RELAY_PIN   22
#define LED_BUILTIN  2

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

// -------------------- Provisioning --------------------
Preferences prefs;
WebServer   provServer(80);
bool        provisioningMode = false;

// -------------------- Runtime config (loaded from Preferences) --------------------
String cfg_wifi_ssid;
String cfg_wifi_pass;
String cfg_mqtt_server;
String cfg_mqtt_user;
String cfg_mqtt_pass;
int    cfg_mqtt_port;
String cfg_network_id;
String cfg_zone_id;
String cfg_device_id;
String cfg_outlet_device_id;

// -------------------- MQTT topic strings (built at runtime) --------------------
String TOPIC_INLET_FLOW;
String TOPIC_INLET_FLOW_LIVE;
String TOPIC_INLET_TOTAL;
String TOPIC_OUTLET_FLOW;
String TOPIC_OUTLET_TOTAL;
String TOPIC_OUTLET_HEARTBEAT;
String TOPIC_VALVE_COMMAND;
String TOPIC_VALVE_STATUS;
String TOPIC_LEAK_ALERT;

// -------------------- MQTT & WiFi Clients --------------------
WiFiClientSecure espClient;
PubSubClient     client(espClient);

// -------------------- Flow Variables --------------------
volatile byte  pulseCount       = 0;
byte           pulse1Sec        = 0;
float          flowRateInlet    = 0.0;
unsigned int   flowMilliLitres  = 0;
unsigned long  totalMilliLitres = 0;
float          flowRateOutlet   = 0.0;
unsigned long  totalOutletML    = 0;
long           previousMillis   = 0;
int            interval         = 1000;
float          calibrationFactor = 6.5;

// -------------------- Valve & Leak Detection --------------------
bool valveState       = true;
bool leakDetected     = false;
int  leakConfirmCount = 0;
const int LEAK_CONFIRM_THRESHOLD = 3;

// -------------------- Heartbeat Watchdog --------------------
unsigned long lastHeartbeatMillis        = 0;
const unsigned long HEARTBEAT_TIMEOUT_MS = 5000;

// -------------------- Leak Threshold --------------------
const float leakThreshold = 0.8;

// -------------------- Settle Window --------------------
bool          isSettling        = false;
unsigned long settleStartMillis = 0;
const unsigned long SETTLE_DURATION_MS = 10000;

// ==================== ISR ====================
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

// ==================== TOPIC BUILDER ====================
void buildTopics() {
  String base        = "aquasense/" + cfg_network_id + "/" + cfg_zone_id + "/" + cfg_device_id;
  String outlet_base = "aquasense/" + cfg_network_id + "/" + cfg_zone_id + "/" + cfg_outlet_device_id;

  TOPIC_INLET_FLOW       = base + "/sensor/inlet/flow_rate";
  TOPIC_INLET_FLOW_LIVE  = base + "/sensor/inlet/live_flow";
  TOPIC_INLET_TOTAL      = base + "/sensor/inlet/total_L";
  TOPIC_OUTLET_FLOW      = outlet_base + "/sensor/outlet/flow_rate";
  TOPIC_OUTLET_TOTAL     = outlet_base + "/sensor/outlet/total_L";
  TOPIC_OUTLET_HEARTBEAT = outlet_base + "/sensor/outlet/heartbeat";
  TOPIC_VALVE_COMMAND    = base + "/valve/command";
  TOPIC_VALVE_STATUS     = base + "/valve/status";
  TOPIC_LEAK_ALERT       = base + "/leak/alert";
}

// ==================== PROVISIONING ====================
void startProvisioningMode() {
  provisioningMode = true;

  // Blink LED to indicate provisioning mode
  pinMode(LED_BUILTIN, OUTPUT);
  for (int i = 0; i < 6; i++) {
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    delay(300);
  }

  String apName = "AquaSense-Setup-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  WiFi.softAP(apName.c_str(), "aquasense123");

  Serial.println("📶 Provisioning mode started");
  Serial.println("AP: " + apName);
  Serial.println("IP: " + WiFi.softAPIP().toString());  // always 192.168.4.1

  // GET /info — app pings this to confirm device is reachable and get chip ID
  provServer.on("/info", HTTP_GET, []() {
    StaticJsonDocument<200> doc;
    doc["chip_id"]     = String((uint32_t)ESP.getEfuseMac(), HEX);
    doc["firmware"]    = "inlet_v1";
    doc["sensor_type"] = "inlet";
    String response;
    serializeJson(doc, response);
    provServer.send(200, "application/json", response);
    Serial.println("📡 /info requested");
  });

  // POST /configure — app sends all credentials here
  provServer.on("/configure", HTTP_POST, []() {
    if (!provServer.hasArg("plain")) {
      provServer.send(400, "application/json", "{\"error\":\"missing body\"}");
      return;
    }

    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, provServer.arg("plain"));
    if (err) {
      provServer.send(400, "application/json", "{\"error\":\"invalid json\"}");
      return;
    }

    // Save all credentials to flash
    prefs.begin("aquasense", false);
    prefs.putString("wifi_ssid",          doc["wifi_ssid"].as<String>());
    prefs.putString("wifi_pass",          doc["wifi_password"].as<String>());
    prefs.putString("mqtt_server",        doc["mqtt_broker_host"].as<String>());
    prefs.putString("mqtt_user",          doc["mqtt_username"].as<String>());
    prefs.putString("mqtt_pass",          doc["mqtt_password"].as<String>());
    prefs.putInt(   "mqtt_port",          doc["mqtt_broker_port"].as<int>());
    prefs.putString("network_id",         doc["network_id"].as<String>());
    prefs.putString("zone_id",            doc["zone_id"].as<String>());
    prefs.putString("device_id",          doc["device_id"].as<String>());
    prefs.putString("outlet_device_id",   doc["outlet_device_id"].as<String>());
    prefs.end();

    provServer.send(200, "application/json", "{\"status\":\"saved\"}");
    Serial.println("✅ Config saved — rebooting...");

    delay(1000);
    ESP.restart();
  });

  // DELETE /reset — clears all saved credentials (factory reset)
  provServer.on("/reset", HTTP_DELETE, []() {
    prefs.begin("aquasense", false);
    prefs.clear();
    prefs.end();
    provServer.send(200, "application/json", "{\"status\":\"reset\"}");
    Serial.println("🔄 Credentials cleared — rebooting into provisioning mode...");
    delay(1000);
    ESP.restart();
  });

  provServer.begin();
}

// ==================== LOAD CONFIG ====================
bool loadConfig() {
  prefs.begin("aquasense", true);  // read-only
  cfg_wifi_ssid        = prefs.getString("wifi_ssid",        "");
  cfg_wifi_pass        = prefs.getString("wifi_pass",        "");
  cfg_mqtt_server      = prefs.getString("mqtt_server",      "");
  cfg_mqtt_user        = prefs.getString("mqtt_user",        "");
  cfg_mqtt_pass        = prefs.getString("mqtt_pass",        "");
  cfg_mqtt_port        = prefs.getInt(   "mqtt_port",        8883);
  cfg_network_id       = prefs.getString("network_id",       "");
  cfg_zone_id          = prefs.getString("zone_id",          "");
  cfg_device_id        = prefs.getString("device_id",        "");
  cfg_outlet_device_id = prefs.getString("outlet_device_id", "");
  prefs.end();

  // All required fields must be present
  return (cfg_wifi_ssid.length() > 0 &&
          cfg_device_id.length() > 0 &&
          cfg_mqtt_server.length() > 0);
}

// ==================== HELPERS ====================
String parseValveCommand(const String& msg) {
  if (msg == "open"  || msg.indexOf("\"open\"")  >= 0) return "open";
  if (msg == "close" || msg.indexOf("\"close\"") >= 0) return "close";
  return "";
}

void startSettleWindow() {
  isSettling        = true;
  settleStartMillis = millis();
  leakConfirmCount  = 0;
  Serial.println("⏳ Settle window started — leak detection paused for 10 s");
}

// ==================== MQTT CALLBACK ====================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("MQTT IN ["); Serial.print(topic); Serial.print("]: ");
  Serial.println(message);

  if (String(topic) == TOPIC_VALVE_COMMAND) {
    String cmd = parseValveCommand(message);

    if (cmd == "open") {
      leakDetected     = false;
      leakConfirmCount = 0;
      openValve();
      startSettleWindow();
      client.publish(TOPIC_VALVE_STATUS.c_str(), "Opened", true);
      client.publish(TOPIC_LEAK_ALERT.c_str(),
        "{\"status\":\"NORMAL\",\"valve\":\"OPEN\"}", true);
      Serial.println("✅ Valve OPENED — settle window active");

    } else if (cmd == "close") {
      isSettling       = false;
      leakDetected     = false;
      leakConfirmCount = 0;
      closeValve();
      client.publish(TOPIC_VALVE_STATUS.c_str(), "Closed", true);
      Serial.println("🔴 Valve CLOSED manually");
    }
  }

  if (String(topic) == TOPIC_OUTLET_FLOW) {
    flowRateOutlet = message.toFloat();
  }
  if (String(topic) == TOPIC_OUTLET_TOTAL) {
    totalOutletML = message.toFloat() * 1000;
  }
  if (String(topic) == TOPIC_OUTLET_HEARTBEAT) {
    lastHeartbeatMillis = millis();
  }
}

// ==================== MQTT RECONNECT ====================
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");

    String clientId = "ESP32-Inlet-" + String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(),
                       cfg_mqtt_user.c_str(),
                       cfg_mqtt_pass.c_str())) {
      Serial.println("✅ MQTT Connected");

      client.subscribe(TOPIC_VALVE_COMMAND.c_str());
      client.subscribe(TOPIC_OUTLET_FLOW.c_str());
      client.subscribe(TOPIC_OUTLET_TOTAL.c_str());
      client.subscribe(TOPIC_OUTLET_HEARTBEAT.c_str());

      client.publish(TOPIC_VALVE_STATUS.c_str(),
                     valveState ? "Opened" : "Closed", true);

      if (leakDetected) {
        client.publish(TOPIC_LEAK_ALERT.c_str(),
          "{\"status\":\"LEAK_DETECTED\",\"valve\":\"CLOSED\",\"note\":\"reconnected\"}",
          true);
      } else {
        client.publish(TOPIC_LEAK_ALERT.c_str(),
          "{\"status\":\"NORMAL\",\"valve\":\"OPEN\"}", true);
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
  digitalWrite(RELAY_PIN, HIGH);  // NC valve: HIGH = open
  pinMode(LED_BUILTIN, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  // ── Boot decision: provisioning or normal mode ────────────────────────
  if (!loadConfig()) {
    Serial.println("⚙️  No config found — entering provisioning mode");
    startProvisioningMode();
    return;  // loop() will handle the provisioning web server
  }

  Serial.println("✅ Config loaded — starting normal mode");

  // ── Connect to saved WiFi ─────────────────────────────────────────────
  WiFi.begin(cfg_wifi_ssid.c_str(), cfg_wifi_pass.c_str());
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected — IP: " + WiFi.localIP().toString());

  // ── Build MQTT topics from loaded config ──────────────────────────────
  buildTopics();

  // ── Connect to MQTT ───────────────────────────────────────────────────
  espClient.setCACert(root_ca);
  client.setServer(cfg_mqtt_server.c_str(), cfg_mqtt_port);
  client.setCallback(mqttCallback);
  client.setKeepAlive(60);
  client.setSocketTimeout(30);
  client.setBufferSize(512);

  lastHeartbeatMillis = millis();
  startSettleWindow();

  Serial.println("✅ Setup complete — AquaSense Inlet Device Ready");
  Serial.println("Device ID: " + cfg_device_id);
}

// ==================== MAIN LOOP ====================
void loop() {
  // ── Provisioning mode: serve the config web server only ──────────────
  if (provisioningMode) {
    provServer.handleClient();
    return;
  }

  // ── Normal mode: full MQTT + leak detection ───────────────────────────
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

    // ── Settle window ───────────────────────────────────────────────────
    if (isSettling) {
      unsigned long elapsed = millis() - settleStartMillis;
      if (elapsed >= SETTLE_DURATION_MS) {
        isSettling       = false;
        leakConfirmCount = 0;
        Serial.print("✅ Settle window expired (");
        Serial.print(elapsed / 1000);
        Serial.println("s) — leak detection resumed");
      }
    }

    // ── Heartbeat watchdog ──────────────────────────────────────────────
    bool outletAlive = (millis() - lastHeartbeatMillis) < HEARTBEAT_TIMEOUT_MS;

    // ── Leak detection ──────────────────────────────────────────────────
    if (outletAlive && !leakDetected && !isSettling) {
      float flowDiff = flowRateInlet - flowRateOutlet;

      if (flowDiff > leakThreshold) {
        leakConfirmCount++;
        Serial.print("⚠️  Leak suspicion count: ");
        Serial.println(leakConfirmCount);

        if (leakConfirmCount >= LEAK_CONFIRM_THRESHOLD) {
          leakDetected     = true;
          leakConfirmCount = 0;
          closeValve();

          char leakPayload[160];
          snprintf(leakPayload, sizeof(leakPayload),
            "{\"status\":\"LEAK_DETECTED\","
            "\"valve\":\"CLOSED\","
            "\"inlet_flow\":%.2f,"
            "\"outlet_flow\":%.2f,"
            "\"diff\":%.2f,"
            "\"threshold\":%.2f}",
            flowRateInlet, flowRateOutlet, flowDiff, leakThreshold
          );

          client.publish(TOPIC_LEAK_ALERT.c_str(),   leakPayload, true);
          client.publish(TOPIC_VALVE_STATUS.c_str(), "Closed",    true);

          Serial.println("🚨 LEAK CONFIRMED — Valve closed.");
        }
      } else {
        if (leakConfirmCount > 0) Serial.println("ℹ️  Delta normalised — counter reset");
        leakConfirmCount = 0;
      }

    } else if (isSettling) {
      leakConfirmCount = 0;
      Serial.print("⏳ Settling... (");
      Serial.print((millis() - settleStartMillis) / 1000);
      Serial.print("s / ");
      Serial.print(SETTLE_DURATION_MS / 1000);
      Serial.println("s)");

    } else if (!outletAlive) {
      leakConfirmCount = 0;
      Serial.println("⚠️  Outlet heartbeat timeout — leak detection suppressed");
    }

    // ── Publish inlet sensor data ────────────────────────────────────────
    char flowRateStr[16];
    char totalLStr[16];
    dtostrf(flowRateInlet,             6, 2, flowRateStr);
    dtostrf(totalMilliLitres / 1000.0, 6, 2, totalLStr);

    client.publish(TOPIC_INLET_FLOW.c_str(),      flowRateStr);
    client.publish(TOPIC_INLET_FLOW_LIVE.c_str(), flowRateStr);
    client.publish(TOPIC_INLET_TOTAL.c_str(),     totalLStr);

    // ── Serial monitor ───────────────────────────────────────────────────
    Serial.println("────────────────────────────────────────────────");
    Serial.print("  INLET   → "); Serial.print(flowRateInlet, 2);
    Serial.print(" L/min | Total: "); Serial.print(totalMilliLitres / 1000.0, 2); Serial.println(" L");
    Serial.print("  OUTLET  → "); Serial.print(flowRateOutlet, 2);
    Serial.print(" L/min | Total: "); Serial.print(totalOutletML / 1000.0, 2); Serial.println(" L");
    Serial.print("  DIFF    → "); Serial.print(flowRateInlet - flowRateOutlet, 2); Serial.println(" L/min");
    Serial.print("  VALVE   → "); Serial.println(valveState   ? "OPEN ✅"     : "CLOSED 🚨");
    Serial.print("  LEAK    → "); Serial.println(leakDetected ? "DETECTED 🚨" : "None ✅");
    Serial.print("  OUTLET  → "); Serial.println(outletAlive  ? "Online ✅"   : "OFFLINE ⚠️");
    Serial.print("  SETTLE  → "); Serial.println(isSettling   ? "YES ⏳"      : "No");
    Serial.println("────────────────────────────────────────────────");
  }
}

// ==================== VALVE CONTROL ====================
void openValve() {
  valveState = true;
  digitalWrite(RELAY_PIN, HIGH);
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("✅ Valve Opened");
}

void closeValve() {
  valveState = false;
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("🚨 Valve Closed");
}