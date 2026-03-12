#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// -------------------- Pins --------------------
#define SENSOR_PIN   26
#define RELAY_PIN    22
#define LED_PIN       2

// -------------------- Wi-Fi Configuration --------------------
// ⚠️ SECURITY: Move these to a secrets.h file and add to .gitignore
#define WIFI_SSID     "Dialog 4G 780"
#define WIFI_PASSWORD "40De7e62"

// -------------------- MQTT / HiveMQ Configuration --------------------
const char* mqtt_server   = "66791e6741b44aecb122ab7b59807177.s1.eu.hivemq.cloud";
const char* mqtt_username = "AquaSense";
const char* mqtt_password = "Aquasense@123@#";
const int   mqtt_port     = 8883;

// -------------------- MQTT Topics --------------------
#define TOPIC_INLET_FLOW    "home/waterflow/inlet/flow_rate"
#define TOPIC_INLET_TOTAL   "home/waterflow/inlet/total_L"
#define TOPIC_OUTLET_FLOW   "home/waterflow/outlet/flow_rate"
#define TOPIC_OUTLET_TOTAL  "home/waterflow/outlet/total_L"
#define TOPIC_VALVE_COMMAND "home/waterflow/valve/command"
#define TOPIC_VALVE_STATUS  "home/waterflow/valve/status"
#define TOPIC_LEAK_ALERT    "home/waterflow/leak/alert"

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

// -------------------- ISR Critical Section Mutex --------------------
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

// -------------------- Flow Variables --------------------
volatile uint16_t pulseCount      = 0;
uint16_t          pulse1Sec       = 0;

float         flowRateInlet    = 0.0;
float         flowRateOutlet   = 0.0;
unsigned long flowMilliLitres  = 0;
unsigned long totalMilliLitres = 0;
unsigned long totalOutletML    = 0;

// -------------------- Timing --------------------
unsigned long previousMillis             = 0;
unsigned long previousTotalPublishMillis = 0;

const unsigned long flowInterval  = 1000; // 1 second
const unsigned long totalInterval = 5000; // 5 seconds

// -------------------- Calibration --------------------
const float calibrationFactor = 6.5;

// -------------------- Outlet Stale Data Detection --------------------
unsigned long lastOutletUpdate          = 0;
const unsigned long OUTLET_STALE_TIMEOUT = 5000; // 5 seconds

// -------------------- Valve & Leak Detection --------------------
bool valveState   = true;  // true = open, false = closed
bool leakDetected = false;

// Adaptive leak detection parameters
const float minThreshold       = 0.6;  // minimum absolute diff (L/min) to flag
const float leakPercent        = 0.20; // flag if diff > 20% of inlet flow
const float minFlowForLeak     = 1.0;  // skip leak check below this inlet flow (L/min)
const int   leakConfirmSeconds = 4;    // consecutive seconds required to confirm leak

int leakCounter = 0;

// ==================== ISR ====================
void IRAM_ATTR pulseCounter() {
  portENTER_CRITICAL_ISR(&mux);
  pulseCount++;
  portEXIT_CRITICAL_ISR(&mux);
}

// ==================== VALVE CONTROL ====================
void openValve() {
  valveState = true;
  digitalWrite(RELAY_PIN, LOW);   // LOW = relay energised = valve open
  digitalWrite(LED_PIN, HIGH);
  Serial.println("✅ Valve Opened");
}

void closeValve() {
  valveState = false;
  digitalWrite(RELAY_PIN, HIGH);  // HIGH = relay de-energised = valve closed
  digitalWrite(LED_PIN, LOW);
  Serial.println("🚨 Valve Closed");
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

  // ---- Valve commands from mobile app ----
  if (String(topic) == TOPIC_VALVE_COMMAND) {

    if (message == "open") {
      // Block manual open if leak is active — user must send reset_leak first
      if (leakDetected) {
        Serial.println("⚠️  Open ignored — leak active. Send 'reset_leak' first.");
        client.publish(TOPIC_VALVE_STATUS, "Leak_Locked", true);
      } else {
        openValve();
        client.publish(TOPIC_VALVE_STATUS, "Opened", true);
      }

    } else if (message == "close") {
      closeValve();
      client.publish(TOPIC_VALVE_STATUS, "Closed", true);

    } else if (message == "reset_leak") {
      // Only accepted if a leak is currently flagged
      if (leakDetected) {
        leakDetected = false;
        leakCounter  = 0;
        openValve();

        // Publish structured JSON reset confirmation
        char resetPayload[96];
        snprintf(resetPayload, sizeof(resetPayload),
          "{\"status\":\"NORMAL\","
          "\"valve\":\"OPENED\","
          "\"reset_by\":\"USER\"}"
        );

        client.publish(TOPIC_LEAK_ALERT,   resetPayload, true);
        client.publish(TOPIC_VALVE_STATUS, "Opened",     true);
        Serial.println("✅ Leak reset by user. Valve reopened.");
      } else {
        Serial.println("ℹ️  reset_leak received but no leak is active.");
      }
    }
  }

  // ---- Outlet flow rate from second ESP32 ----
  if (String(topic) == TOPIC_OUTLET_FLOW) {
    flowRateOutlet   = message.toFloat();
    lastOutletUpdate = millis(); // refresh staleness timer
  }

  // ---- Outlet total from second ESP32 ----
  if (String(topic) == TOPIC_OUTLET_TOTAL) {
    totalOutletML = (unsigned long)(message.toFloat() * 1000.0); // L → mL
  }
}

// ==================== WIFI ====================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Wi-Fi Connected — IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n❌ Wi-Fi failed. Will retry on next loop.");
  }
}

// ==================== MQTT RECONNECT ====================
void reconnectMQTT() {
  int retries = 0;
  while (!client.connected() && retries < 5) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32-Inlet-" + String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("✅ MQTT Connected");

      // Subscribe to all required topics
      client.subscribe(TOPIC_VALVE_COMMAND);
      client.subscribe(TOPIC_OUTLET_FLOW);
      client.subscribe(TOPIC_OUTLET_TOTAL);

      // Publish true current state on reconnect (not hardcoded "Opened")
      client.publish(TOPIC_VALVE_STATUS, valveState ? "Opened" : "Closed", true);

      // Republish current leak state so app is in sync after reconnect
      if (leakDetected) {
        client.publish(TOPIC_LEAK_ALERT,
          "{\"status\":\"LEAK_DETECTED\",\"valve\":\"CLOSED\",\"note\":\"reconnected\"}",
          true
        );
      } else {
        client.publish(TOPIC_LEAK_ALERT,
          "{\"status\":\"NORMAL\",\"valve\":\"OPENED\"}",
          true
        );
      }

    } else {
      Serial.print("❌ MQTT failed rc=");
      Serial.print(client.state());
      Serial.println(" — retrying in 5s");
      delay(5000);
      retries++;
    }
  }
}

// ==================== LEAK DETECTION ====================
void checkLeak() {

  // Gate 1: Skip if outlet data is stale (outlet ESP32 offline)
  if (millis() - lastOutletUpdate > OUTLET_STALE_TIMEOUT) {
    Serial.println("⚠️  Outlet data stale — skipping leak check");
    leakCounter = 0;
    return;
  }

  // Gate 2: Skip at very low flow — readings unreliable
  if (flowRateInlet < minFlowForLeak) {
    leakCounter = 0;
    return;
  }

  // Gate 3: Already locked — valve is closed, nothing more to do
  if (leakDetected) {
    return;
  }

  // Gate 4: Adaptive threshold — scales with flow rate
  float leakThreshold = max(minThreshold, leakPercent * flowRateInlet);
  float diff          = flowRateInlet - flowRateOutlet;

  if (diff > leakThreshold) {
    leakCounter++;

    Serial.print("⚠️  Leak candidate | diff: ");
    Serial.print(diff, 2);
    Serial.print(" L/min | threshold: ");
    Serial.print(leakThreshold, 2);
    Serial.print(" | counter: ");
    Serial.print(leakCounter);
    Serial.print("/");
    Serial.println(leakConfirmSeconds);

    // Gate 5: Confirmed only after N consecutive seconds
    if (leakCounter >= leakConfirmSeconds) {
      leakDetected = true;
      closeValve();
      leakCounter = 0;

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
        diff,
        leakThreshold
      );

      client.publish(TOPIC_LEAK_ALERT,   leakPayload, true); // retained
      client.publish(TOPIC_VALVE_STATUS, "Closed",    true); // retained

      Serial.println("🚨 LEAK CONFIRMED — Valve permanently closed!");
      Serial.print("   Inlet: "); Serial.print(flowRateInlet, 2);
      Serial.print(" | Outlet: "); Serial.print(flowRateOutlet, 2);
      Serial.print(" | Diff: "); Serial.println(diff, 2);
    }

  } else {
    // Difference is within normal range — reset counter
    if (leakCounter > 0) {
      Serial.println("✅ Diff normalised — leak counter reset");
    }
    leakCounter = 0;
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);

  pinMode(SENSOR_PIN, INPUT_PULLUP);
  pinMode(RELAY_PIN,  OUTPUT);
  pinMode(LED_PIN,    OUTPUT);

  // Start with valve open
  openValve();

  // Attach flow sensor interrupt
  attachInterrupt(digitalPinToInterrupt(SENSOR_PIN), pulseCounter, FALLING);

  // Connect WiFi
  connectWiFi();

  // Configure MQTT over TLS
  espClient.setCACert(root_ca);
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setKeepAlive(60);
  client.setSocketTimeout(30);

  Serial.println("✅ Setup complete — AquaSense Inlet Device Ready");
}

// ==================== MAIN LOOP ====================
void loop() {

  // Handle WiFi dropout
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️  WiFi lost — reconnecting...");
    connectWiFi();
    return;
  }

  // Handle MQTT dropout
  if (!client.connected()) reconnectMQTT();
  client.loop();

  unsigned long currentMillis = millis();

  // ---- Flow rate calculation — every 1 second ----
  if (currentMillis - previousMillis >= flowInterval) {
    previousMillis = currentMillis;

    // Safely read and clear pulse count
    portENTER_CRITICAL(&mux);
    pulse1Sec  = pulseCount;
    pulseCount = 0;
    portEXIT_CRITICAL(&mux);

    // Convert pulses to flow rate and accumulate volume
    flowRateInlet    = ((1000.0 / (float)flowInterval) * pulse1Sec) / calibrationFactor;
    flowMilliLitres  = (unsigned long)((flowRateInlet / 60.0) * 1000.0);
    totalMilliLitres += flowMilliLitres;

    // Run leak check every second
    checkLeak();

    // Publish live inlet flow rate
    char flowRateStr[16];
    dtostrf(flowRateInlet, 4, 2, flowRateStr);
    client.publish(TOPIC_INLET_FLOW, flowRateStr);
  }

  // ---- Total volume publish — every 5 seconds ----
  if (currentMillis - previousTotalPublishMillis >= totalInterval) {
    previousTotalPublishMillis = currentMillis;

    float totalLiters = totalMilliLitres / 1000.0;
    char  totalLStr[16];
    dtostrf(totalLiters, 6, 2, totalLStr);
    client.publish(TOPIC_INLET_TOTAL, totalLStr);

    // Serial monitor summary
    Serial.println("────────────────────────────────────────");
    Serial.print("  INLET  → ");
    Serial.print(flowRateInlet, 2);
    Serial.print(" L/min | Total: ");
    Serial.print(totalLiters, 2);
    Serial.println(" L");
    Serial.print("  OUTLET → ");
    Serial.print(flowRateOutlet, 2);
    Serial.print(" L/min | Total: ");
    Serial.print(totalOutletML / 1000.0, 2);
    Serial.println(" L");
    Serial.print("  DIFF   → ");
    Serial.print(flowRateInlet - flowRateOutlet, 2);
    Serial.println(" L/min");
    Serial.print("  VALVE  → ");
    Serial.println(valveState ? "OPEN ✅" : "CLOSED 🚨");
    Serial.print("  LEAK   → ");
    Serial.println(leakDetected ? "DETECTED 🚨" : "None ✅");
    Serial.println("────────────────────────────────────────");
  }
}
