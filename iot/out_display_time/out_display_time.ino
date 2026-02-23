#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// -------------------- Pins --------------------
#define SENSOR 27
#define LED_BUILTIN 2

// -------------------- Wi-Fi Configuration --------------------
#define WIFI_SSID "Dialog 4G 780"
#define WIFI_PASSWORD "40De7e62"

// -------------------- MQTT / HiveMQ Configuration --------------------
const char* mqtt_server = "66791e6741b44aecb122ab7b59807177.s1.eu.hivemq.cloud";
const char* mqtt_username = "AquaSense";
const char* mqtt_password = "Aquasense@123@#";
const int mqtt_port = 8883;

// MQTT Topics
#define TOPIC_OUTLET_FLOW "home/waterflow/sensor2/flow_rate"
#define TOPIC_OUTLET_TOTAL "home/waterflow/sensor2/total_L"

// -------------------- Root CA Certificate --------------------
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

WiFiClientSecure espClient;
PubSubClient client(espClient);

// -------------------- Flow Variables --------------------
volatile byte pulseCount = 0;
byte pulse1Sec = 0;
float flowRate = 0.0;
unsigned int flowMilliLitres = 0;
unsigned long totalMilliLitres = 0;

long previousFlowMillis = 0;
long previousTotalPublishMillis = 0;

int flowInterval = 1000;     // 1 second for live flow
int totalInterval = 5000;    // 5 seconds for total usage

float calibrationFactor = 6.5;

// -------------------- ISR --------------------
void IRAM_ATTR pulseCounter() {
  pulseCount++;
}

// -------------------- MQTT Connection --------------------
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32-Outlet-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("✅ MQTT Connected");
    } else {
      Serial.print("❌ Failed, rc=");
      Serial.print(client.state());
      Serial.println(" Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  delay(2000);  // allow serial to stabilize

  Serial.println("ESP32 Outlet Booting...");

  pinMode(SENSOR, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(SENSOR), pulseCounter, FALLING);

  Serial.println("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  Serial.println("\nWiFi Connected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

// --- MQTT Setup ---
  espClient.setCACert(root_ca);
  client.setServer(mqtt_server, mqtt_port);
  client.setKeepAlive(60);
  client.setSocketTimeout(30);

  Serial.println("✅ MQTT Configured");
}

// -------------------- Main Loop --------------------
void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  long currentMillis = millis();

  // ---- FLOW RATE (1 SECOND) ----
  if (currentMillis - previousFlowMillis > flowInterval) {

    pulse1Sec = pulseCount;
    pulseCount = 0;
    previousFlowMillis = currentMillis;

    flowRate = ((1000.0 / flowInterval) * pulse1Sec) / calibrationFactor;  // L/min
    flowMilliLitres = (flowRate / 60.0) * 1000.0;
    totalMilliLitres += flowMilliLitres;

    // Publish Flow Rate (1 decimal)
    char flowRateStr[10];
    dtostrf(flowRate, 4, 1, flowRateStr);
    client.publish(TOPIC_OUTLET_FLOW, flowRateStr);

    // LED blink
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }

  // ---- TOTAL USAGE (EVERY 5 SECONDS) ----
  if (currentMillis - previousTotalPublishMillis > totalInterval) {
    previousTotalPublishMillis = currentMillis;

    float totalLiters = totalMilliLitres / 1000.0;

    char totalLStr[10];
    dtostrf(totalLiters, 6, 1, totalLStr);
    client.publish(TOPIC_OUTLET_TOTAL, totalLStr);

    Serial.print("Outlet Flow: ");
    Serial.print(flowRate, 1);
    Serial.print(" L/min, Total: ");
    Serial.print(totalLiters, 1);
    Serial.println(" L");
  }
}
