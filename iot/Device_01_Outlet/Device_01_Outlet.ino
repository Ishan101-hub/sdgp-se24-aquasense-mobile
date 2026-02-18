#include <WiFi.h>
#include <esp_now.h>

// -------------------- Pins --------------------
#define SENSOR 27
#define LED_BUILTIN 2

// -------------------- Flow Variables --------------------
volatile byte pulseCount = 0;
byte pulse1Sec = 0;
float flowRate = 0.0;
unsigned int flowMilliLitres = 0;
unsigned long totalMilliLitres = 0;
long previousMillis = 0;
int interval = 1000;
float calibrationFactor = 6.5;

// -------------------- ESP-NOW --------------------
typedef struct struct_message {
  float outletFlowRate;
  unsigned long outletTotalML;
} struct_message;

struct_message dataToSend;

//  Change this to your INLET (Device 02) MAC address
uint8_t receiverAddress[] = {0xC0, 0xCD, 0xD6, 0xCA, 0x11, 0x9C};

void IRAM_ATTR pulseCounter() { pulseCount++; }

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SENSOR, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("❌ ESP-NOW init failed");
    return;
  }

  esp_now_peer_info_t peerInfo{};
  memcpy(peerInfo.peer_addr, receiverAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  Serial.println("✅ Outlet Device Ready");
}

void loop() {
  long currentMillis = millis();
  if (currentMillis - previousMillis > interval) {
    pulse1Sec = pulseCount;
    pulseCount = 0;
    flowRate = ((1000.0 / (currentMillis - previousMillis)) * pulse1Sec) / calibrationFactor;
    previousMillis = currentMillis;

    flowMilliLitres = (flowRate / 60) * 1000;
    totalMilliLitres += flowMilliLitres;

    // Prepare data to send
    dataToSend.outletFlowRate = flowRate;
    dataToSend.outletTotalML = totalMilliLitres;
    esp_now_send(receiverAddress, (uint8_t *)&dataToSend, sizeof(dataToSend));

    // Display on Serial
    Serial.print("Flow rate: ");
    Serial.print(flowRate, 2);
    Serial.print(" L/min\tOutput Liquid: ");
    Serial.print(totalMilliLitres);
    Serial.print(" mL / ");
    Serial.print(totalMilliLitres / 1000.0);
    Serial.println(" L");
  }
}
