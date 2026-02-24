#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// -------------------- Pins --------------------
#define SENSOR_PIN  27
#define LED_PIN      2

// -------------------- Wi-Fi Configuration --------------------
// ⚠️ SECURITY: Move these to a secrets.h file and add to .gitignore
#define WIFI_SSID     "Dialog 4G 780"
#define WIFI_PASSWORD "40De7e62"

// -------------------- MQTT / HiveMQ Configuration --------------------
const char* mqtt_server   = "66791e6741b44aecb122ab7b59807177.s1.eu.hivemq.cloud";
const char* mqtt_username = "AquaSense";
const char* mqtt_password = "Aquasense@123@#";
const int   mqtt_port     = 8883;

// -------------------- MQTT Topics --------------------
#define TOPIC_OUTLET_FLOW  "home/waterflow/outlet/flow_rate"
#define TOPIC_OUTLET_TOTAL "home/waterflow/outlet/total_L"

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

// -------------------- ISR Critical Section Mutex --------------------
// FIX #1: Protect shared ISR variable from race conditions
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

// -------------------- Flow Variables --------------------
// FIX #2: Changed volatile byte -> volatile uint16_t to prevent overflow
volatile uint16_t pulseCount = 0;
uint16_t          pulse1Sec  = 0;

float         flowRateOutlet  = 0.0;
// FIX #6: Changed unsigned int -> unsigned long to prevent volume overflow
unsigned long flowMilliLitres = 0;
unsigned long totalMilliLitres = 0;

// FIX #11: Changed long -> unsigned long to prevent millis() rollover
unsigned long previousFlowMillis         = 0;
unsigned long previousTotalPublishMillis = 0;

const unsigned long flowInterval  = 1000; // 1 second
const unsigned long totalInterval = 5000; // 5 seconds
const float calibrationFactor     = 6.5;

// -------------------- Moving Average --------------------
#define MA_SIZE 3
float flowBuffer[MA_SIZE] = {0.0, 0.0, 0.0};
int   bufferIndex         = 0;

// -------------------- ISR --------------------
// FIX #1: Use critical section in ISR
void IRAM_ATTR pulseCounter() {
  portENTER_CRITICAL_ISR(&mux);
  pulseCount++;
  portEXIT_CRITICAL_ISR(&mux);
}

// -------------------- WiFi Connection --------------------
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Wi-Fi Connected — IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n❌ Wi-Fi failed. Will retry.");
  }
}

// -------------------- MQTT Reconnection --------------------
void reconnectMQTT() {
  int retries = 0;
  while (!client.connected() && retries < 5) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32-Outlet-" + String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("✅ MQTT Connected");
    } else {
      Serial.print("❌ MQTT failed rc=");
      Serial.print(client.state());
      Serial.println(" — retrying in 5s");
      delay(5000);
      retries++;
    }
  }
}

// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(SENSOR_PIN, INPUT_PULLUP);
  pinMode(LED_PIN,    OUTPUT);
  digitalWrite(LED_PIN, LOW);

  attachInterrupt(digitalPinToInterrupt(SENSOR_PIN), pulseCounter, FALLING);

  connectWiFi();

  espClient.setCACert(root_ca);
  client.setServer(mqtt_server, mqtt_port);
  client.setKeepAlive(60);
  client.setSocketTimeout(30);

  Serial.println("✅ Setup complete");
}

// -------------------- Main Loop --------------------
void loop() {
  // FIX #13: Handle WiFi dropout
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️  WiFi lost — reconnecting...");
    connectWiFi();
    return;
  }

  if (!client.connected()) reconnectMQTT();
  client.loop();

  unsigned long currentMillis = millis();

  // ---- Flow rate — every 1 second ----
  if (currentMillis - previousFlowMillis >= flowInterval) {
    previousFlowMillis = currentMillis;

    // FIX #1: Safely read and clear pulse count using critical section
    portENTER_CRITICAL(&mux);
    pulse1Sec  = pulseCount;
    pulseCount = 0;
    portEXIT_CRITICAL(&mux);

    flowRateOutlet  = ((1000.0 / (float)flowInterval) * pulse1Sec) / calibrationFactor;
    flowMilliLitres = (unsigned long)((flowRateOutlet / 60.0) * 1000.0);
    totalMilliLitres += flowMilliLitres;

    // Moving average smoothing (publishes smoothed rate, accumulates raw volume — correct)
    flowBuffer[bufferIndex] = flowRateOutlet;
    bufferIndex = (bufferIndex + 1) % MA_SIZE;

    float avgFlow = 0.0;
    for (int i = 0; i < MA_SIZE; i++) avgFlow += flowBuffer[i];
    avgFlow /= MA_SIZE;

    // Publish smoothed outlet flow rate
    // FIX #12: Increased buffer to 16
    char flowRateStr[16];
    dtostrf(avgFlow, 4, 2, flowRateStr);
    client.publish(TOPIC_OUTLET_FLOW, flowRateStr);

    // LED heartbeat blink
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  }

  // ---- Total usage — every 5 seconds ----
  if (currentMillis - previousTotalPublishMillis >= totalInterval) {
    previousTotalPublishMillis = currentMillis;

    float totalLiters = totalMilliLitres / 1000.0;
    char  totalLStr[16];
    dtostrf(totalLiters, 6, 2, totalLStr);
    client.publish(TOPIC_OUTLET_TOTAL, totalLStr);

    Serial.print("[ OUTLET ] ");
    Serial.print(flowRateOutlet, 2);
    Serial.print(" L/min | Total: ");
    Serial.print(totalLiters, 2);
    Serial.println(" L");
  }
}
