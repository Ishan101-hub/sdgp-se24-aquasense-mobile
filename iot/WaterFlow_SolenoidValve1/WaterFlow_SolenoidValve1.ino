#include <WiFi.h>
#include <FirebaseESP32.h>

// -------------------- Firebase Configuration --------------------
#define FIREBASE_HOST ""       // Your Firebase Realtime Database URL
#define FIREBASE_AUTH ""       // Your Firebase Database Secret or Token

// -------------------- WiFi Credentials --------------------
#define WIFI_SSID ""           // Your WiFi SSID
#define WIFI_PASSWORD ""       // Your WiFi Password

// -------------------- Hardware Pins --------------------
#define RELAY_PIN 22           // Relay module control pin
#define SENSOR_PIN 27          // Flow sensor signal pin
#define LED_BUILTIN 2          // Status LED

// -------------------- Firebase Setup --------------------
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// -------------------- Flow Sensor Variables --------------------
volatile byte pulseCount;       // Counts pulses from flow sensor
byte pulse1Sec = 0;
float flowRate;
unsigned int flowMilliLitres;
unsigned long totalMilliLitres;
long previousMillisFlow = 0;
int intervalFlow = 1000;        // 1 second
float calibrationFactor = 6.5;  // Adjust based on your sensor

// -------------------- Valve Control Variables --------------------
bool valveState = false;
unsigned long lastCheckValve = 0;
int checkIntervalValve = 2000; // Firebase read every 2 seconds

// -------------------- Interrupt Service Routine --------------------
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

// -------------------- Setup Function --------------------
void setup() {
  Serial.begin(115200);

  // Pins setup
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // Start with valve closed
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);

  pulseCount = 0;
  flowRate = 0;
  flowMilliLitres = 0;
  totalMilliLitres = 0;

  attachInterrupt(digitalPinToInterrupt(SENSOR_PIN), pulseCounter, FALLING);

  // -------------------- WiFi Connection --------------------
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Connected to WiFi");

  // -------------------- Firebase Setup --------------------
  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  Serial.println("✅ Firebase Connected & System Ready");

  // Initial valve state upload
  Firebase.setString(fbdo, "/valve/status", "Closed");
  Firebase.setBool(fbdo, "/valve/state", false);
}

// -------------------- Main Loop --------------------
void loop() {
  unsigned long currentMillis = millis();

  // -------------------- Flow Sensor Calculation --------------------
  if (currentMillis - previousMillisFlow >= intervalFlow) {
    pulse1Sec = pulseCount;
    pulseCount = 0;

    // Flow rate in L/min
    flowRate = ((1000.0 / (millis() - previousMillisFlow)) * pulse1Sec) / calibrationFactor;
    previousMillisFlow = millis();

    // Convert to mL and accumulate
    flowMilliLitres = (flowRate / 60.0) * 1000;
    totalMilliLitres += flowMilliLitres;

    // Serial output
    Serial.print("Flow rate: ");
    Serial.print(flowRate, 2);
    Serial.print(" L/min\tTotal Volume: ");
    Serial.print(totalMilliLitres);
    Serial.print(" mL / ");
    Serial.print(totalMilliLitres / 1000.0);
    Serial.println(" L");

    // Upload to Firebase
    if (Firebase.ready()) {
      Firebase.setFloat(fbdo, "/flow_sensor/flow_rate_Lmin", flowRate);
      Firebase.setInt(fbdo, "/flow_sensor/total_volume_mL", totalMilliLitres);
      Firebase.setString(fbdo, "/flow_sensor/status", "Active");

      if (fbdo.httpCode() == 200) {
        digitalWrite(LED_BUILTIN, HIGH);
        delay(100);
        digitalWrite(LED_BUILTIN, LOW);
      } else {
        Serial.print("❌ Firebase Error: ");
        Serial.println(fbdo.errorReason());
      }
    }
  }

  // -------------------- Valve Control via Firebase --------------------
  if (currentMillis - lastCheckValve >= checkIntervalValve) {
    lastCheckValve = currentMillis;

    if (Firebase.ready()) {
      if (Firebase.getBool(fbdo, "/valve/command")) {
        bool remoteCommand = fbdo.boolData();
        if (remoteCommand != valveState) {
          valveState = remoteCommand;
          updateValveState();
          Serial.println("🔥 Remote Command Executed from Firebase");
        }
      } else {
        Serial.print("⚠️ Firebase Read Error: ");
        Serial.println(fbdo.errorReason());
      }
    }
  }
}

// -------------------- Helper Function --------------------
void updateValveState() {
  digitalWrite(RELAY_PIN, valveState ? HIGH : LOW);

  if (valveState) {
    Serial.println("💧 Valve Opened");
    Firebase.setString(fbdo, "/valve/status", "Opened");
    Firebase.setBool(fbdo, "/valve/state", true);
  } else {
    Serial.println("🔒 Valve Closed");
    Firebase.setString(fbdo, "/valve/status", "Closed");
    Firebase.setBool(fbdo, "/valve/state", false);
  }
}
