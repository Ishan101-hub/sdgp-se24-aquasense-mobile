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
#define NETWORK_ID  "home_01"
#define ZONE_ID     "bathroom_01"
#define DEVICE_ID   "pipe_01_inlet"

// Separate base for the outlet device's topics
#define OUTLET_DEVICE_ID "pipe_01_outlet"
#define OUTLET_BASE      "aquasense/" NETWORK_ID "/" ZONE_ID "/" OUTLET_DEVICE_ID

#define BASE        "aquasense/" NETWORK_ID "/" ZONE_ID "/" DEVICE_ID

// Sensor data
#define TOPIC_INLET_FLOW        BASE "/sensor/inlet/flow_rate"
#define TOPIC_INLET_FLOW_LIVE   BASE "/sensor/inlet/live_flow"
#define TOPIC_INLET_TOTAL       BASE "/sensor/inlet/total_L"

#define TOPIC_OUTLET_FLOW       OUTLET_BASE "/sensor/outlet/flow_rate"
#define TOPIC_OUTLET_TOTAL      OUTLET_BASE "/sensor/outlet/total_L"
#define TOPIC_OUTLET_HEARTBEAT  OUTLET_BASE "/sensor/outlet/heartbeat"

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
bool valveState       = true;   // true = open (NC relay energised)
bool leakDetected     = false;  // Stays true until user manually re-opens valve from app
int  leakConfirmCount = 0;
const int LEAK_CONFIRM_THRESHOLD = 3;  // Consecutive seconds above threshold before confirming leak

// -------------------- Heartbeat Watchdog --------------------
// The inlet ESP32 checks whether the outlet ESP32 is alive before running
// leak detection. If no heartbeat is received within HEARTBEAT_TIMEOUT_MS,
// leak detection is suppressed to prevent false positives from a missing
// outlet reading.
unsigned long lastHeartbeatMillis        = 0;
const unsigned long HEARTBEAT_TIMEOUT_MS = 5000;  // 5 seconds

// -------------------- Leak Threshold --------------------
// Must match server: config.FLOW_MISMATCH_THRESHOLD_LPM = 0.8
const float leakThreshold = 0.8;  // L/min difference to flag as potential leak

// ==================== SETTLE WINDOW ====================
//
// PURPOSE: Suppress false leak detection immediately after the valve opens.
//
// PROBLEM: When the valve opens, inlet flow rises within the first pump
// stroke (~0-2 seconds). Outlet flow only rises after water travels through
// the pipe to reach the outlet sensor (~3-8 seconds depending on pipe length
// and pressure). During this stabilisation gap the delta (inlet - outlet)
// easily exceeds leakThreshold, and if the mismatch lasts 3 consecutive
// seconds the system falsely reports a leak.
//
// FIX: Immediately upon receiving an "open" valve command, set isSettling=true
// and record the start time. While settling, the leak detection block is
// completely skipped and leakConfirmCount is reset every tick. After
// SETTLE_DURATION_MS the flag is cleared and normal detection resumes.
//
// This must match the server backup detector:
//   leak_service.py → SETTLE_WINDOW_SECONDS = 10
//   leak_service.py → force_settle() is called by mobile_valve_command on open
//
bool          isSettling        = false;
unsigned long settleStartMillis = 0;
const unsigned long SETTLE_DURATION_MS = 10000;  // 10 seconds — must match server


// -------------------- ISR --------------------
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

// ==================== HELPERS ====================

// Parse an incoming MQTT valve command.
// Server sends plain text "open" or "close".
// Also accepts JSON {"valve":"open"} for forward compatibility.
String parseValveCommand(const String& msg) {
  if (msg == "open"  || msg.indexOf("\"open\"")  >= 0) return "open";
  if (msg == "close" || msg.indexOf("\"close\"") >= 0) return "close";
  return "";
}

// Start the settle window unconditionally.
// Called whenever the valve opens for ANY reason (command from app, or on boot).
// Resets the leak confirmation counter so any counts accumulated before the
// valve opened (from a prior flow event) do not carry over.
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

  Serial.print("MQTT IN [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // ── Valve commands from mobile app / server backup detector ────────────
  if (String(topic) == TOPIC_VALVE_COMMAND) {
    String cmd = parseValveCommand(message);

    if (cmd == "open") {
      // ── User opens valve (normal operation or after fixing a leak) ───────
      // Step 1: clear leak state so the confirmation counter starts fresh
      leakDetected     = false;
      leakConfirmCount = 0;

      // Step 2: physically open the relay
      openValve();

      // Step 3: start the settle window BEFORE publishing any status.
      // The settle window suppresses leak detection for SETTLE_DURATION_MS
      // so the transient inlet/outlet flow mismatch during pipe pressurisation
      // does not trigger a false alarm.
      // The server backup detector mirrors this via force_settle() in
      // mobile_valve_command (leak_service.py → force_settle).
      startSettleWindow();

      // Step 4: publish updated state so server and app stay in sync.
      // retained=true ensures late-connecting subscribers see current state.
      client.publish(TOPIC_VALVE_STATUS, "Opened", true);
      client.publish(TOPIC_LEAK_ALERT,   "{\"status\":\"NORMAL\",\"valve\":\"OPEN\"}", true);

      Serial.println("✅ Valve OPENED — settle window active");

    } else if (cmd == "close") {
      // ── User manually closes valve from app ──────────────────────────────
      // Cancel any active settle window — flow will drop to 0 so there is
      // nothing to settle. Reset leak state to allow re-detection after the
      // valve is next opened.
      isSettling       = false;
      leakDetected     = false;
      leakConfirmCount = 0;
      closeValve();
      client.publish(TOPIC_VALVE_STATUS, "Closed", true);

      Serial.println("🔴 Valve CLOSED manually");
    }
  }

  // ── Outlet flow data published by the outlet ESP32 ─────────────────────
  // The inlet ESP32 subscribes to these topics to read the outlet sensor
  // values for its local leak detection comparison.
  if (String(topic) == TOPIC_OUTLET_FLOW) {
    flowRateOutlet = message.toFloat();
  }
  if (String(topic) == TOPIC_OUTLET_TOTAL) {
    totalOutletML = message.toFloat() * 1000;  // L → mL for internal accounting
  }

  // ── Heartbeat from outlet ESP32 ─────────────────────────────────────────
  // Receiving a heartbeat means the outlet ESP32 is alive and its flow
  // readings are fresh. Without a heartbeat, outletAlive becomes false and
  // leak detection is suppressed (prevents false positives from stale data).
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

      // Publish the actual current valve state on reconnect so the server
      // and app always reflect the physical position after a drop.
      client.publish(TOPIC_VALVE_STATUS, valveState ? "Opened" : "Closed", true);

      // Republish current leak state so app re-syncs after reconnect
      if (leakDetected) {
        client.publish(TOPIC_LEAK_ALERT,
          "{\"status\":\"LEAK_DETECTED\",\"valve\":\"CLOSED\",\"note\":\"reconnected\"}",
          true
        );
      } else {
        client.publish(TOPIC_LEAK_ALERT,
          "{\"status\":\"NORMAL\",\"valve\":\"OPEN\"}",
          true
        );
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

  // NC (Normally-Closed) solenoid valve: HIGH energises the relay coil,
  // which pulls the NC contact open → water flows.
  digitalWrite(RELAY_PIN, HIGH);

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

  // Initialise heartbeat timer so the watchdog does not trip immediately.
  // The outlet ESP32 has 5 seconds to send its first heartbeat.
  lastHeartbeatMillis = millis();

  // Start with a settle window at boot.
  // The NC valve opens the moment RELAY_PIN goes HIGH (above). Inlet flow
  // will rise within the first second; outlet flow takes several seconds to
  // follow. Starting the settle window here prevents a false leak alarm
  // during the initial pipe-pressurisation transient.
  startSettleWindow();

  Serial.println("✅ Setup complete — AquaSense Inlet Device Ready");
  Serial.println("📡 Publishing to: " BASE);
}

// ==================== MAIN LOOP ====================
void loop() {
  if (!client.connected()) reconnectMQTT();

  // Process incoming MQTT messages. If an "open" command arrives here,
  // mqttCallback sets isSettling=true BEFORE the 1-second timer block runs
  // its leak check, so the settle window is always active when detection fires.
  client.loop();

  long currentMillis = millis();

  if (currentMillis - previousMillis > interval) {
    pulse1Sec  = pulseCount;
    pulseCount = 0;
    previousMillis = currentMillis;

    // Calculate inlet flow rate from pulse count
    flowRateInlet    = ((1000.0 / interval) * pulse1Sec) / calibrationFactor;
    flowMilliLitres  = (flowRateInlet / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    // ── Settle window management ────────────────────────────────────────────
    // The settle window expires when SETTLE_DURATION_MS has elapsed since
    // the valve opened. At expiry:
    //   • isSettling is cleared so leak detection resumes next tick
    //   • leakConfirmCount is reset so any spurious counts accumulated during
    //     settling (should be 0 anyway due to the reset in the else-if below)
    //     do not carry over into the active detection window
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

    // ── Heartbeat watchdog ──────────────────────────────────────────────────
    // Matches server: HEARTBEAT_TIMEOUT_SEC (also 5 s).
    bool outletAlive = (millis() - lastHeartbeatMillis) < HEARTBEAT_TIMEOUT_MS;

    // ── Leak detection ──────────────────────────────────────────────────────
    // All three guards must be true before the mismatch counter increments:
    //   • outletAlive  — outlet ESP32 is sending fresh readings
    //   • !leakDetected — no already-confirmed leak (avoids re-triggering)
    //   • !isSettling   — settle window has expired (avoids valve-open transient)
    if (outletAlive && !leakDetected && !isSettling) {
      float flowDiff = flowRateInlet - flowRateOutlet;

      if (flowDiff > leakThreshold) {
        leakConfirmCount++;
        Serial.print("⚠️  Leak suspicion count: ");
        Serial.println(leakConfirmCount);

        if (leakConfirmCount >= LEAK_CONFIRM_THRESHOLD) {
          // ── Leak confirmed ────────────────────────────────────────────────
          leakDetected     = true;
          leakConfirmCount = 0;
          closeValve();

          // Build JSON payload matching server _process_event_message() spec
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

          // retained=true so server gets the alert even after a brief disconnect
          client.publish(TOPIC_LEAK_ALERT,   leakPayload, true);
          client.publish(TOPIC_VALVE_STATUS, "Closed",    true);

          Serial.println("🚨 LEAK CONFIRMED — Valve closed. Open from app to reset.");
        }
      } else {
        // Delta is below threshold — reset counter (must be consecutive seconds)
        if (leakConfirmCount > 0) {
          Serial.println("ℹ️  Delta normalised — counter reset");
        }
        leakConfirmCount = 0;
      }

    } else if (isSettling) {
      // During the settle window, zero the counter every tick so that no
      // suspicion counts accumulated just before or during settling carry
      // over into the active detection window when the window expires.
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
    // leakDetected=true case: valve already closed, just wait for user action

    // ── Publish inlet sensor data ────────────────────────────────────────────
    char flowRateStr[16];
    char totalLStr[16];

    dtostrf(flowRateInlet,             6, 2, flowRateStr);
    dtostrf(totalMilliLitres / 1000.0, 6, 2, totalLStr);

    client.publish(TOPIC_INLET_FLOW,      flowRateStr);
    client.publish(TOPIC_INLET_FLOW_LIVE, flowRateStr);
    client.publish(TOPIC_INLET_TOTAL,     totalLStr);

    // ── Serial monitor ───────────────────────────────────────────────────────
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
  digitalWrite(RELAY_PIN, HIGH);   // Energise relay coil → NC contact opens → water flows
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("✅ Valve Opened");
}

void closeValve() {
  valveState = false;
  digitalWrite(RELAY_PIN, LOW);    // De-energise relay coil → NC contact closes → water blocked
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("🚨 Valve Closed");
}
