#include <WiFi.h>
#include <FirebaseESP32.h>

// -------------------- Firebase Configuration --------------------
#define FIREBASE_HOST ""       // Your Firebase Realtime Database URL
#define FIREBASE_AUTH ""       // Your Firebase Database Secret or Token

// -------------------- WiFi Credentials --------------------
#define WIFI_SSID ""           // Your WiFi SSID
#define WIFI_PASSWORD ""       // Your WiFi Password

// -------------------- Hardware Pins --------------------
#define SENSOR_INLET 25        // Inlet YF-S201
#define SENSOR_OUTLET 26       // Outlet YF-S201
#define RELAY_PIN 22           // Solenoid valve control (cuts inlet water)
#define LED_BUILTIN 2          // ESP32 onboard LED

// -------------------- Firebase Objects --------------------
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// -------------------- Flow Sensor Variables --------------------
volatile byte pulseCountInlet = 0;
volatile byte pulseCountOutlet = 0;

float calibrationFactor = 6.5;   // Adjust based on your YF-S201
float flowRateInlet = 0.0;
float flowRateOutlet = 0.0;

unsigned long totalMilliLitresInlet = 0;
unsigned long totalMilliLitresOutlet = 0;

unsigned long prevMillisInlet = 0;
unsigned long prevMillisOutlet = 0;
int interval = 1000; // 1 second

// -------------------- Valve and Leak Control --------------------
bool valveState = true; // true = open, false = closed
bool leakDetected = false;

// -------------------- Interrupt Service Routines --------------------
void IRAM_ATTR pulseCounterInlet() {
  pulseCountInlet++;
}
void IRAM_ATTR pulseCounterOutlet() {
  pulseCountOutlet++;
}

// -------------------- Setup Function --------------------
void setup() {
  Serial.begin(115200);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Start valve open
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SENSOR_INLET, INPUT_PULLUP);
  pinMode(SENSOR_OUTLET, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(SENSOR_INLET), pulseCounterInlet, FALLING);
  attachInterrupt(digitalPinToInterrupt(SENSOR_OUTLET), pulseCounterOutlet, FALLING);

  // -------------------- Connect to WiFi --------------------
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

  // Initial Firebase state
  Firebase.setString(fbdo, "/valve/status", "Opened");
  Firebase.setBool(fbdo, "/valve/state", true);
  Firebase.setString(fbdo, "/alert/status", "Normal");
}

// -------------------- Main Loop --------------------
void loop() {
  unsigned long currentMillis = millis();

  // -------------------- Inlet Flow Calculation --------------------
  if (currentMillis - prevMillisInlet >= interval) {
    detachInterrupt(SENSOR_INLET);
    float pulseInlet = pulseCountInlet;
    pulseCountInlet = 0;
    flowRateInlet = ((1000.0 / (millis() - prevMillisInlet)) * pulseInlet) / calibrationFactor;
    prevMillisInlet = millis();
    totalMilliLitresInlet += (flowRateInlet / 60.0) * 1000;
    attachInterrupt(digitalPinToInterrupt(SENSOR_INLET), pulseCounterInlet, FALLING);
  }

  // -------------------- Outlet Flow Calculation --------------------
  if (currentMillis - prevMillisOutlet >= interval) {
    detachInterrupt(SENSOR_OUTLET);
    float pulseOutlet = pulseCountOutlet;
    pulseCountOutlet = 0;
    flowRateOutlet = ((1000.0 / (millis() - prevMillisOutlet)) * pulseOutlet) / calibrationFactor;
    prevMillisOutlet = millis();
    totalMilliLitresOutlet += (flowRateOutlet / 60.0) * 1000;
    attachInterrupt(digitalPinToInterrupt(SENSOR_OUTLET), pulseCounterOutlet, FALLING);
  }

  // -------------------- Leak Detection Logic --------------------
  if (flowRateInlet > 0 && (flowRateInlet - flowRateOutlet) > 2.0) {
    // Leak detected if outlet flow significantly less than inlet
    if (!leakDetected) {
      leakDetected = true;
      closeValve();
      Serial.println("🚨 Leakage Detected! Valve Closed.");
      Firebase.setString(fbdo, "/alert/status", "Leakage Detected - Valve Closed");
    }
  } else {
    // No leak — open valve if previously closed
    if (leakDetected) {
      leakDetected = false;
      openValve();
      Serial.println("✅ Leak Cleared. Valve Opened.");
      Firebase.setString(fbdo, "/alert/status", "Normal");
    }
  }

  // -------------------- Upload Sensor Data --------------------
  if (Firebase.ready()) {
    Firebase.setFloat(fbdo, "/flow/inlet_rate_Lmin", flowRateInlet);
    Firebase.setFloat(fbdo, "/flow/outlet_rate_Lmin", flowRateOutlet);
    Firebase.setInt(fbdo, "/flow/inlet_total_mL", totalMilliLitresInlet);
    Firebase.setInt(fbdo, "/flow/outlet_total_mL", totalMilliLitresOutlet);
  }

  // -------------------- Serial Output --------------------
  Serial.print("Inlet: ");
  Serial.print(flowRateInlet, 2);
  Serial.print(" L/min | Outlet: ");
  Serial.print(flowRateOutlet, 2);
  Serial.print(" L/min | Valve: ");
  Serial.println(valveState ? "OPEN" : "CLOSED");

  delay(1000);
}

// -------------------- Helper Functions --------------------
void openValve() {
  valveState = true;
  digitalWrite(RELAY_PIN, LOW); // Open inlet (relay off)
  Firebase.setString(fbdo, "/valve/status", "Opened");
  Firebase.setBool(fbdo, "/valve/state", true);
  digitalWrite(LED_BUILTIN, HIGH);
}

void closeValve() {
  valveState = false;
  digitalWrite(RELAY_PIN, HIGH); // Close inlet (relay on)
  Firebase.setString(fbdo, "/valve/status", "Closed");
  Firebase.setBool(fbdo, "/valve/state", false);
  digitalWrite(LED_BUILTIN, LOW);
}
