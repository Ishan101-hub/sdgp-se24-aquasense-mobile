#include <WiFi.h>
#include <esp_now.h>
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

// -------------------- States --------------------
bool valveState = true;
bool leakDetected = false;
unsigned long lastFirebaseCheck = 0;
int firebaseCheckInterval = 2000;

// -------------------- ESP-NOW --------------------
typedef struct struct_message {
  float outletFlowRate;
  unsigned long outletTotalML;
} struct_message;

struct_message incomingData;

void IRAM_ATTR pulseCounter() { pulseCount++; }



void onDataRecv(const esp_now_recv_info *recv_info, const uint8_t *incomingDataBytes, int len){
  memcpy(&incomingData, incomingDataBytes, sizeof(incomingData));
  flowRateOutlet = incomingData.outletFlowRate;
  totalOutletML = incomingData.outletTotalML;
}



// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SENSOR, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("❌ ESP-NOW init failed");
    return;
  }
  esp_now_register_recv_cb(onDataRecv);


  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  WiFi.setChannel(6);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  Serial.println("\n✅ Inlet Device Ready & Firebase Connected");

  Firebase.setString(fbdo, "/valve/status", "Opened");
  Firebase.setBool(fbdo, "/valve/state", true);
}

// -------------------- Loop --------------------
void loop() {
  long currentMillis = millis();

  // --- Flow calculation each second ---
  if (currentMillis - previousMillis > interval) {
    pulse1Sec = pulseCount;
    pulseCount = 0;
    flowRateInlet = ((1000.0 / (currentMillis - previousMillis)) * pulse1Sec) / calibrationFactor;
    previousMillis = currentMillis;
    flowMilliLitres = (flowRateInlet / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    // --- Display local data ---
    Serial.print("Inlet: ");
    Serial.print(flowRateInlet, 2);
    Serial.print(" L/min (");
    Serial.print(totalMilliLitres / 1000.0);
    Serial.print(" L used)\tOutlet: ");
    Serial.print(flowRateOutlet, 2);
    Serial.print(" L/min (");
    Serial.print(totalOutletML / 1000.0);
    Serial.println(" L used)");

    // --- Leak detection logic ---
    if (flowRateInlet > 0 && (flowRateInlet - flowRateOutlet) > 2.0) {
      if (!leakDetected) {
        leakDetected = true;
        closeValve();
        Firebase.setString(fbdo, "/alert/status", "Leak Detected – Valve Closed");
      }
    } else if (leakDetected && (flowRateInlet - flowRateOutlet) < 1.0) {
      leakDetected = false;
      openValve();
      Firebase.setString(fbdo, "/alert/status", "Normal");
    }

    // --- Upload data to Firebase ---
    if (Firebase.ready()) {
      Firebase.setFloat(fbdo, "/flow/inlet_rate_Lmin", flowRateInlet);
      Firebase.setFloat(fbdo, "/flow/outlet_rate_Lmin", flowRateOutlet);
      
      Firebase.setFloat(fbdo, "/usage/inlet_total_L", totalMilliLitres / 1000.0);
      Firebase.setFloat(fbdo, "/usage/outlet_total_L", totalOutletML / 1000.0);
      Firebase.setString(fbdo, "/valve/status", valveState ? "Opened" : "Closed");
    }
  }

  // --- Manual override from Firebase every 2 s ---
  if (currentMillis - lastFirebaseCheck >= firebaseCheckInterval) {
    lastFirebaseCheck = currentMillis;
    if (Firebase.getBool(fbdo, "/valve/manual_command")) {
      bool remoteCmd = fbdo.boolData();
      if (remoteCmd != valveState) {
        if (remoteCmd) openValve(); else closeValve();
        Firebase.setString(fbdo, "/valve/status", remoteCmd ? "Opened (Manual)" : "Closed (Manual)");
      }
    }
  }
}

// -------------------- Helper Functions --------------------
void openValve() {
  valveState = true;
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("✅ Valve Opened");
}

void closeValve() {
  valveState = false;
  digitalWrite(RELAY_PIN, HIGH);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("🚨 Valve Closed");
}
