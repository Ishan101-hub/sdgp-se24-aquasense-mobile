#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>          // <-- needed to set channel on esp-idf v5

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

uint8_t receiverAddress[] = {0xc0, 0xcd, 0xd6, 0xca, 0x11, 0x9c};

// --- interrupt ---
void IRAM_ATTR pulseCounter() { pulseCount++; }

// --- send callback matching esp-idf v5 signature ---
void onDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  // status: 0 = success, 1 = fail
  Serial.print("ESP-NOW send status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
  // Optionally inspect info if needed (not all fields are printable)
}

// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SENSOR, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  // Put WiFi in STA mode and set the channel to match inlet device
  WiFi.mode(WIFI_STA);
  // choose channel number both devices must use - change to the channel your inlet uses
  const int espNowChannel = 6;
  esp_wifi_set_channel(espNowChannel, WIFI_SECOND_CHAN_NONE); // requires esp_wifi.h

  // init ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("❌ ESP-NOW init failed");
    while (true) delay(1000);
  }

  // register send callback (correct signature for esp-idf v5)
  esp_now_register_send_cb(onDataSent);

  // add peer - channel must match the channel set above
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, receiverAddress, 6);
  peerInfo.channel = espNowChannel;  // must match esp_wifi_set_channel above
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("❌ Failed to add peer");
    // continue anyway to allow debugging
  }

  Serial.println("✅ Outlet Device Ready");
}

// -------------------- Loop --------------------
void loop() {
  long currentMillis = millis();
  if (currentMillis - previousMillis > interval) {
    pulse1Sec = pulseCount;
    pulseCount = 0;

    // avoid division by zero
    long elapsed = currentMillis - previousMillis;
    if (elapsed <= 0) elapsed = 1;

    flowRate = ((1000.0 / (float)elapsed) * pulse1Sec) / calibrationFactor;
    previousMillis = currentMillis;

    flowMilliLitres = (flowRate / 60.0) * 1000.0;
    totalMilliLitres += flowMilliLitres;

    // Prepare data to send
    dataToSend.outletFlowRate = flowRate;
    dataToSend.outletTotalML = totalMilliLitres;

    // send - check return (0 = success)
    esp_err_t res = esp_now_send(receiverAddress, (uint8_t *)&dataToSend, sizeof(dataToSend));
    if (res == ESP_OK) {
      // actual status will be reported via onDataSent callback
    } else {
      Serial.print("esp_now_send returned error: ");
      Serial.println(res);
    }

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
