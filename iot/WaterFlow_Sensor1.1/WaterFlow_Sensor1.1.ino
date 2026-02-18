#include <WiFi.h>
#include <FirebaseESP32.h>

// -------------------- Firebase Configuration --------------------
#define FIREBASE_HOST "https://projectv2--se24-default-rtdb.firebaseio.com/"        // Your Firebase Realtime Database URL
#define FIREBASE_AUTH "hUp5vivb6OieTrZpRei1sg5j4l0VZpESCcEGxWCv"        // Your Firebase Database Secret or Token

// -------------------- WiFi Credentials --------------------
#define WIFI_SSID "L"            // Your WiFi SSID
#define WIFI_PASSWORD "Lammi123"        // Your WiFi Password

// -------------------- Hardware Pins --------------------
#define LED_BUILTIN 2
#define SENSOR 27               // Flow sensor signal pin

// -------------------- Firebase Objects --------------------
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// -------------------- Flow Sensor Variables --------------------
long currentMillis = 0;
long previousMillis = 0;
int interval = 1000;            // 1 second
float calibrationFactor = 6.5;  // Adjust based on your sensor
volatile byte pulseCount;       // Counts pulses from flow sensor
byte pulse1Sec = 0;
float flowRate;
unsigned int flowMilliLitres;
unsigned long totalMilliLitres;

// -------------------- Interrupt Service Routine --------------------
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

// -------------------- Setup Function --------------------
void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SENSOR, INPUT_PULLUP);

  pulseCount = 0;
  flowRate = 0.0;
  flowMilliLitres = 0;
  totalMilliLitres = 0;
  previousMillis = 0;

  // Attach interrupt for flow sensor
  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

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
}

// -------------------- Main Loop --------------------
void loop() {
  currentMillis = millis();

  if (currentMillis - previousMillis > interval) {
    pulse1Sec = pulseCount;
    pulseCount = 0;

    // Calculate flow rate in L/min
    flowRate = ((1000.0 / (millis() - previousMillis)) * pulse1Sec) / calibrationFactor;
    previousMillis = millis();

    // Convert to millilitres per second and accumulate
    flowMilliLitres = (flowRate / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    // Print values to Serial Monitor
    Serial.print("Flow rate: ");
    Serial.print(flowRate, 2);
    Serial.print(" L/min\t");

    Serial.print("Total Volume: ");
    Serial.print(totalMilliLitres);
    Serial.print(" mL / ");
    Serial.print(totalMilliLitres / 1000.0);
    Serial.println(" L");

    // -------------------- Upload to Firebase --------------------
    if (Firebase.ready()) {
      Firebase.setFloat(fbdo, "/flow_sensor/flow_rate_Lmin", flowRate);
      Firebase.setInt(fbdo, "/flow_sensor/total_volume_mL", totalMilliLitres);
      Firebase.setString(fbdo, "/flow_sensor/status", "Active");

      if (fbdo.httpCode() == 200) {
        digitalWrite(LED_BUILTIN, HIGH);  // Blink LED to show success
        delay(100);
        digitalWrite(LED_BUILTIN, LOW);
      } else {
        Serial.print("❌ Firebase Error: ");
        Serial.println(fbdo.errorReason());
      }
    }
  }
}
