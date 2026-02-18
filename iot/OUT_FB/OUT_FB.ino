#include <WiFi.h>
#include <FirebaseESP32.h>

// -------------------- Pins --------------------
#define SENSOR 27
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
float flowRate = 0.0;
unsigned int flowMilliLitres = 0;
unsigned long totalMilliLitres = 0;
long previousMillis = 0;
int interval = 1000;           // Update every 1 second
float calibrationFactor = 6.5; // Adjust according to your flow sensor

// -------------------- ISR --------------------
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  // --- Connect Wi-Fi ---
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected");

  // --- Firebase setup ---
  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  Serial.println("✅ Firebase Connected");
}

void loop() {
  long currentMillis = millis();

  // --- Flow calculation each second ---
  if (currentMillis - previousMillis > interval) {
    pulse1Sec = pulseCount;
    pulseCount = 0;
    previousMillis = currentMillis;

    flowRate = ((1000.0 / interval) * pulse1Sec) / calibrationFactor;       // L/min
    flowMilliLitres = (flowRate / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    // --- Update Firebase ---
    if (Firebase.ready()) {
      Firebase.setFloat(fbdo, "/outlet/flow_rate_Lmin", flowRate);
      Firebase.setFloat(fbdo, "/outlet/total_L", totalMilliLitres / 1000.0);
    }

    // --- Serial monitor ---
    Serial.print("Outlet Flow: ");
    Serial.print(flowRate, 2);
    Serial.print(" L/min, Total: ");
    Serial.print(totalMilliLitres / 1000.0);
    Serial.println(" L");

    // --- LED blink ---
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }
}
