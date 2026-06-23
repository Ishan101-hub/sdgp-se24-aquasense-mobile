# AquaSense Architecture

AquaSense follows a distributed IoT architecture with four main layers.

## 1. Hardware / IoT Layer

The hardware layer includes ESP32 microcontrollers, YF-S201 flow sensors, relay modules, and solenoid valves. The ESP32 reads water flow pulses, calculates flow rates and volume, publishes sensor data through MQTT, and executes valve control commands.

## 2. MQTT Communication Layer

HiveMQ Cloud is used as the MQTT broker. ESP32 devices publish sensor readings and receive valve commands using structured topics.

Example topic pattern:

```text
aquasense/{network_id}/{zone_id}/{device_id}/readings
aquasense/{network_id}/{zone_id}/{device_id}/valve/command
```

## 3. Backend Layer

The backend is implemented with FastAPI. It manages:

- HTTP API routes
- Authentication and account security
- MQTT subscription and publishing
- Leak detection service
- Database writes and batch flushing
- Scheduled aggregation
- Analytics endpoints

### Backend Internal Flow

```mermaid
flowchart TD
    Main[main.py]
    Config[config.py]
    MQTT[mqtt_service.py]
    Leak[leak_service.py]
    DB[(Supabase PostgreSQL)]
    Routers[API Routers]
    Flutter[Flutter App]

    Main --> Config
    Main --> MQTT
    Main --> Leak
    Main --> Routers
    MQTT --> Leak
    MQTT --> DB
    Leak --> DB
    Routers --> DB
    Flutter --> Routers
```

## 4. Frontend Layer

The frontend is built with Flutter using a modular layered structure:

- `screens/` for full pages
- `widgets/` for reusable UI components
- `services/` for API and storage logic
- `models/` for data models
- `theme_provider.dart` for theme state

## Data Flow

```mermaid
sequenceDiagram
    participant ESP32
    participant HiveMQ
    participant FastAPI
    participant Supabase
    participant Flutter

    ESP32->>HiveMQ: Publish flow readings
    HiveMQ->>FastAPI: MQTT subscription
    FastAPI->>FastAPI: Validate + detect leaks
    FastAPI->>Supabase: Store readings/events
    Flutter->>FastAPI: HTTPS API request
    FastAPI->>Supabase: Query summaries
    FastAPI-->>Flutter: JSON response
    FastAPI->>HiveMQ: Valve command if required
    HiveMQ->>ESP32: Close/open valve
```
