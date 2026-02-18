// ESP32 - Solenoid Valve Control via Relay


const int relayPin = 22;   // GPIO pin connected to relay IN
const int buttonPin = 18;  // Optional manual button
bool valveState = false;

void setup() {
  Serial.begin(115200);
  pinMode(relayPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP);
  digitalWrite(relayPin, LOW);  // Ensure valve starts OFF (closed)

  Serial.println("System Initialized: Solenoid Valve Control Ready");
}

void loop() {
  // Optional: Manual control with button
  if (digitalRead(buttonPin) == LOW) {
    delay(200); // debounce delay
    valveState = !valveState;
    digitalWrite(relayPin, valveState ? HIGH : LOW);

    if (valveState) {
      Serial.println("Valve Opened (Relay ON)");
    } else {
      Serial.println("Valve Closed (Relay OFF)");
    }
  }

  // Example: automatic toggle every 5 seconds (for testing)
  // Comment this out if using button control
  delay(5000);
  valveState = !valveState;
  digitalWrite(relayPin, valveState ? HIGH : LOW);
  Serial.println(valveState ? "Valve Opened (Auto)" : "Valve Closed (Auto)");
}
