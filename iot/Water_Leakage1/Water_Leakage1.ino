#include <WiFi.h>
#include <FirebaseESP32.h>




// Firebase Configuration
#define FIREBASE_HOST "https://projectv2--se24-default-rtdb.firebaseio.com/"
#define FIREBASE_AUTH "hUp5vivb6OieTrZpRei1sg5j4l0VZpESCcEGxWCv"

// WiFi Credentials
#define WIFI_SSID "Home wifi"
#define WIFI_PASSWORD "Eshani123"

// Hardware Pins
#define SENSOR1 25
#define SENSOR2 26
#define RELAY 5 // Controls the solenoid valve (inlet)
#define BUZZER 12

FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// Flow Sensor Variables
volatile byte pulseCount1 = 0;
volatile byte pulseCount2 = 0;
float calibrationFactor = 6.0;
float flowRate1, flowRate2;
unsigned long totalMilliLitres1 = 0;
unsigned long totalMilliLitres2 = 0;
unsigned long previousMillis1 = 0;
unsigned long previousMillis2 = 0;
int interval = 1000;

// Interrupts
void IRAM_ATTR pulseCounter1() { pulseCount1++; }
void IRAM_ATTR pulseCounter2() { pulseCount2++; }

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");

  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);



  pinMode(SENSOR1, INPUT_PULLUP);
  pinMode(SENSOR2, INPUT_PULLUP);
  pinMode(RELAY, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  digitalWrite(RELAY, LOW);
  digitalWrite(BUZZER, LOW);

  attachInterrupt(digitalPinToInterrupt(SENSOR1), pulseCounter1, FALLING);
  attachInterrupt(digitalPinToInterrupt(SENSOR2), pulseCounter2, FALLING);
}

void loop() {
  unsigned long currentMillis = millis();

  // Inlet Flow
  if (currentMillis - previousMillis1 > interval) {
    detachInterrupt(SENSOR1);
    flowRate1 = ((1000.0 / (millis() - previousMillis1)) * pulseCount1) / calibrationFactor;
    previousMillis1 = millis();
    pulseCount1 = 0;
    totalMilliLitres1 += (flowRate1 / 60) * 1000;
    attachInterrupt(digitalPinToInterrupt(SENSOR1), pulseCounter1, FALLING);
  }

  // Outlet Flow
  if (currentMillis - previousMillis2 > interval) {
    detachInterrupt(SENSOR2);
    flowRate2 = ((1000.0 / (millis() - previousMillis2)) * pulseCount2) / calibrationFactor;
    previousMillis2 = millis();
    pulseCount2 = 0;
    totalMilliLitres2 += (flowRate2 / 60) * 1000;
    attachInterrupt(digitalPinToInterrupt(SENSOR2), pulseCounter2, FALLING);
  }

  

  // Upload Data to Firebase
  Firebase.setFloat(fbdo, "/flow/inlet_rate", flowRate1);
  Firebase.setFloat(fbdo, "/flow/outlet_rate", flowRate2);
  Firebase.setInt(fbdo, "/flow/inlet_total", totalMilliLitres1);
  Firebase.setInt(fbdo, "/flow/outlet_total", totalMilliLitres2);

  // Leak Detection Logic
  if (flowRate2 < flowRate1 && flowRate2 < 8) {
    Serial.println("Leakage Detected!");
    lcd.clear();
    lcd.print("Leak Detected!");
    digitalWrite(RELAY, HIGH);  // Close solenoid valve (no more inlet flow)
    digitalWrite(BUZZER, HIGH);
    Firebase.setString(fbdo, "/alert/status", "Leakage Detected - Valve Closed");
  } else {
    digitalWrite(RELAY, LOW);   // Keep valve open
    digitalWrite(BUZZER, LOW);
    Firebase.setString(fbdo, "/alert/status", "Normal");
  }

  delay(1000);
}
