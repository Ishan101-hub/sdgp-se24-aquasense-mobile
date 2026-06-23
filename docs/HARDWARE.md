# Hardware Documentation

AquaSense uses low-cost IoT components to monitor water flow and control valves.

## Components

| Component | Purpose |
|---|---|
| ESP32 Wi-Fi Development Board | Main microcontroller for sensor reading, MQTT communication, and valve control |
| YF-S201 Water Flow Sensor | Measures water flow rate using Hall-effect pulses |
| 12V Normally Closed Solenoid Valve | Selectively closes water line during leaks |
| Relay Module | Allows ESP32 to control the 12V valve circuit |
| ESP32 Expansion Shield | Simplifies wiring and power distribution |
| 5V / 12V Power Adapters | Powers ESP32 and valve system |
| Jumper Wires | Circuit connections |
| Wi-Fi Router | Network access for MQTT communication |

## Device Responsibilities

The ESP32 firmware:

- Reads flow sensor pulse counts
- Calculates flow rate and volume
- Publishes readings to HiveMQ MQTT broker
- Receives valve commands from backend
- Controls relay and solenoid valve
- Stores valve state where required
- Handles Wi-Fi and MQTT reconnection

## Leak Detection Concept

The system compares inlet and outlet flow readings. When the difference exceeds the configured threshold for multiple readings, the leak service creates a leak event and triggers valve closure.

Default threshold:

```env
FLOW_MISMATCH_THRESHOLD_LPM=0.8
LEAK_CONFIRM_COUNT=3
```

## Future Hardware Enhancements

- GSM module for non-Wi-Fi operation
- Battery backup / UPS
- Improved waterproof casing
- Additional zone support
- Calibration interface from mobile app
