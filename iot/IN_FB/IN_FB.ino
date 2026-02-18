#include <WiFi.h>
#include <FirebaseESP32.h>

// -------------------- Pins --------------------
#define SENSOR 26
#define RELAY_PIN 22
#define LED_BUILTIN 2

// -------------------- Wi-Fi / Firebase --------------------
#define WIFI_SSID "Home wifi"
#define WIFI_PASSWORD "Eshani123"
#define FIREBASE_HOST "https://projectv2--se24-default-rtdb.firebaseio.com/"
#define FIREBASE_AUTH "hUp5vivb6OieTrZpRei1sg5j4l0VZpESCcEGxWCv"

// -------------------- Firebase Objects --------------------
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// -------------------- Flow Variables --------------------
volatile byte pulseCount = 0;
byte pulse1Sec = 0;
float flowRateInlet = 0.0;
unsigned int flowMilliLitres = 0;
unsigned long totalMilliLitres = 0;
float flowRateOutlet = 0.0;
unsigned long totalOutletML = 0;
long previousMillis = 0;
int interval = 1000;
float calibrationFactor = 6.5;

// -------------------- Valve & Leak Detection --------------------
bool valveState = true;   // true = open
bool leakDetected = false;

// ISR for inlet sensor
void IRAM_ATTR pulseCounter() { pulseCount++; }

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR, INPUT_PULLUP);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Valve initially open
  pinMode(LED_BUILTIN, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  // --- Wi-Fi ---
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected");

  // --- Firebase ---
  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  Serial.println("✅ Firebase Connected");

  Firebase.setString(fbdo, "/valve/status", "Opened");
  Firebase.setBool(fbdo, "/valve/state", true);
}

void loop() {
  long currentMillis = millis();

  // --- Inlet Flow Calculation ---
  if (currentMillis - previousMillis > interval) {
    pulse1Sec = pulseCount;
    pulseCount = 0;
    previousMillis = currentMillis;

    flowRateInlet = ((1000.0 / interval) * pulse1Sec) / calibrationFactor; // L/min
    flowMilliLitres = (flowRateInlet / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    // --- Read outlet data from Firebase ---
    if (Firebase.ready() && Firebase.getFloat(fbdo, "/outlet/flow_rate_Lmin")) {
      flowRateOutlet = fbdo.floatData();
    }
    if (Firebase.ready() && Firebase.getFloat(fbdo, "/outlet/total_L")) {
      totalOutletML = fbdo.floatData() * 1000; // convert L to mL
    }

    // --- Leak detection ---
    float leakThreshold = 2.0;       // Threshold to detect leak
    float restoreThreshold = 0.5;    // Threshold to restore flow

    if (!leakDetected && (flowRateInlet - flowRateOutlet) > leakThreshold) {
        leakDetected = true;
        closeValve();
        Firebase.setString(fbdo, "/alert/status", "Leak Detected - Valve Closed");
    } 
    else if (leakDetected && (flowRateInlet - flowRateOutlet) < restoreThreshold) {
          leakDetected = false;
          openValve();
          Firebase.setString(fbdo, "/alert/status", "Normal");
    }

    // --- Upload data to Firebase ---
    if (Firebase.ready()) {
      Firebase.setFloat(fbdo, "/inlet/flow_rate_Lmin", flowRateInlet);
      Firebase.setFloat(fbdo, "/inlet/total_L", totalMilliLitres / 1000.0);

      Firebase.setFloat(fbdo, "/outlet/flow_rate_Lmin", flowRateOutlet);
      Firebase.setFloat(fbdo, "/outlet/total_L", totalOutletML / 1000.0);

      Firebase.setString(fbdo, "/valve/status", valveState ? "Opened" : "Closed");
    }

    // --- Serial monitor ---
    Serial.print("Inlet: "); Serial.print(flowRateInlet,2); Serial.print(" L/min (");
    Serial.print(totalMilliLitres / 1000.0); Serial.print(" L) | ");
    Serial.print("Outlet: "); Serial.print(flowRateOutlet,2); Serial.print(" L/min (");
    Serial.print(totalOutletML / 1000.0); Serial.println(" L)");
  }
}

// -------------------- Valve Control --------------------
void openValve() {
  valveState = true;
  digitalWrite(RELAY_PIN, LOW); // Activate valve relay logic
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("✅ Valve Opened");
}

void closeValve() {
  valveState = false;
  digitalWrite(RELAY_PIN, HIGH); // Deactivate valve relay logic
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("🚨 Valve Closed");
}
