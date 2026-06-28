//---------------OUTLET — with SoftAP Provisioning----------------

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ArduinoJson.h>

// -------------------- Pins --------------------
#define SENSOR      27
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

// -------------------- Runtime config --------------------
String cfg_wifi_ssid;
String cfg_wifi_pass;
String cfg_mqtt_server;
String cfg_mqtt_user;
String cfg_mqtt_pass;
int    cfg_mqtt_port;
String cfg_network_id;
String cfg_zone_id;
String cfg_device_id;

// -------------------- MQTT topic strings --------------------
String TOPIC_OUTLET_FLOW;
String TOPIC_OUTLET_TOTAL;
String TOPIC_OUTLET_HEARTBEAT;

// -------------------- MQTT & WiFi Clients --------------------
WiFiClientSecure espClient;
PubSubClient     client(espClient);

// -------------------- Flow Variables --------------------
volatile byte  pulseCount       = 0;
byte           pulse1Sec        = 0;
float          flowRate         = 0.0;
unsigned int   flowMilliLitres  = 0;
unsigned long  totalMilliLitres = 0;
long           previousMillis   = 0;
int            interval         = 1000;
float          calibrationFactor = 6.5;

// -------------------- Heartbeat --------------------
long previousHeartbeatMillis = 0;
const int heartbeatInterval  = 1000;

// ==================== ISR ====================
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

// ==================== TOPIC BUILDER ====================
void buildTopics() {
  String base         = "aquasense/" + cfg_network_id + "/" + cfg_zone_id + "/" + cfg_device_id;
  TOPIC_OUTLET_FLOW      = base + "/sensor/outlet/flow_rate";
  TOPIC_OUTLET_TOTAL     = base + "/sensor/outlet/total_L";
  TOPIC_OUTLET_HEARTBEAT = base + "/sensor/outlet/heartbeat";
}

// ==================== PROVISIONING ====================
void startProvisioningMode() {
  provisioningMode = true;

  pinMode(LED_BUILTIN, OUTPUT);
  for (int i = 0; i < 6; i++) {
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    delay(300);
  }

  String apName = "AquaSense-Setup-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  WiFi.softAP(apName.c_str(), "aquasense123");

  Serial.println("📶 Provisioning mode started");
  Serial.println("AP: " + apName);
  Serial.println("IP: " + WiFi.softAPIP().toString());

  provServer.on("/info", HTTP_GET, []() {
    StaticJsonDocument<200> doc;
    doc["chip_id"]     = String((uint32_t)ESP.getEfuseMac(), HEX);
    doc["firmware"]    = "outlet_v1";
    doc["sensor_type"] = "outlet";
    String response;
    serializeJson(doc, response);
    provServer.send(200, "application/json", response);
    Serial.println("📡 /info requested");
  });

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

    prefs.begin("aquasense", false);
    prefs.putString("wifi_ssid",   doc["wifi_ssid"].as<String>());
    prefs.putString("wifi_pass",   doc["wifi_password"].as<String>());
    prefs.putString("mqtt_server", doc["mqtt_broker_host"].as<String>());
    prefs.putString("mqtt_user",   doc["mqtt_username"].as<String>());
    prefs.putString("mqtt_pass",   doc["mqtt_password"].as<String>());
    prefs.putInt(   "mqtt_port",   doc["mqtt_broker_port"].as<int>());
    prefs.putString("network_id",  doc["network_id"].as<String>());
    prefs.putString("zone_id",     doc["zone_id"].as<String>());
    prefs.putString("device_id",   doc["device_id"].as<String>());
    prefs.end();

    provServer.send(200, "application/json", "{\"status\":\"saved\"}");
    Serial.println("✅ Config saved — rebooting...");
    delay(1000);
    ESP.restart();
  });

  provServer.on("/reset", HTTP_DELETE, []() {
    prefs.begin("aquasense", false);
    prefs.clear();
    prefs.end();
    provServer.send(200, "application/json", "{\"status\":\"reset\"}");
    Serial.println("🔄 Credentials cleared — rebooting...");
    delay(1000);
    ESP.restart();
  });

  provServer.begin();
}

// ==================== LOAD CONFIG ====================
bool loadConfig() {
  prefs.begin("aquasense", true);
  cfg_wifi_ssid   = prefs.getString("wifi_ssid",   "");
  cfg_wifi_pass   = prefs.getString("wifi_pass",   "");
  cfg_mqtt_server = prefs.getString("mqtt_server", "");
  cfg_mqtt_user   = prefs.getString("mqtt_user",   "");
  cfg_mqtt_pass   = prefs.getString("mqtt_pass",   "");
  cfg_mqtt_port   = prefs.getInt(   "mqtt_port",   8883);
  cfg_network_id  = prefs.getString("network_id",  "");
  cfg_zone_id     = prefs.getString("zone_id",     "");
  cfg_device_id   = prefs.getString("device_id",   "");
  prefs.end();

  return (cfg_wifi_ssid.length() > 0 &&
          cfg_device_id.length() > 0 &&
          cfg_mqtt_server.length() > 0);
}

// ==================== MQTT RECONNECT ====================
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32-Outlet-" + String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(),
                       cfg_mqtt_user.c_str(),
                       cfg_mqtt_pass.c_str())) {
      Serial.println("✅ MQTT Connected");
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
  pinMode(LED_BUILTIN, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  if (!loadConfig()) {
    Serial.println("⚙️  No config found — entering provisioning mode");
    startProvisioningMode();
    return;
  }

  Serial.println("✅ Config loaded — starting normal mode");

  WiFi.begin(cfg_wifi_ssid.c_str(), cfg_wifi_pass.c_str());
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected — IP: " + WiFi.localIP().toString());

  buildTopics();

  espClient.setCACert(root_ca);
  client.setServer(cfg_mqtt_server.c_str(), cfg_mqtt_port);
  client.setKeepAlive(60);
  client.setSocketTimeout(30);
  client.setBufferSize(512);

  Serial.println("✅ Setup complete — AquaSense Outlet Device Ready");
  Serial.println("Device ID: " + cfg_device_id);
}

// ==================== MAIN LOOP ====================
void loop() {
  if (provisioningMode) {
    provServer.handleClient();
    return;
  }

  if (!client.connected()) reconnectMQTT();
  client.loop();

  long currentMillis = millis();

  if (currentMillis - previousMillis > interval) {
    pulse1Sec  = pulseCount;
    pulseCount = 0;
    previousMillis = currentMillis;

    flowRate         = ((1000.0 / interval) * pulse1Sec) / calibrationFactor;
    flowMilliLitres  = (flowRate / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    char flowRateStr[16];
    char totalLStr[16];
    dtostrf(flowRate,                  6, 2, flowRateStr);
    dtostrf(totalMilliLitres / 1000.0, 6, 2, totalLStr);

    client.publish(TOPIC_OUTLET_FLOW.c_str(),  flowRateStr);
    client.publish(TOPIC_OUTLET_TOTAL.c_str(), totalLStr);

    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));

    Serial.print("Outlet Flow: "); Serial.print(flowRate, 2);
    Serial.print(" L/min | Total: ");
    Serial.print(totalMilliLitres / 1000.0, 2); Serial.println(" L");
  }

  if (currentMillis - previousHeartbeatMillis > heartbeatInterval) {
    previousHeartbeatMillis = currentMillis;
    client.publish(TOPIC_OUTLET_HEARTBEAT.c_str(), "1");
  }
}