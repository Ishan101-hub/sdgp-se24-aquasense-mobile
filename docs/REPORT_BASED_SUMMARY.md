# Report-Based Project Summary

This repository documentation is based on the AquaSense SDGP group report.

## Main Components

- Flutter frontend
- FastAPI backend
- Supabase PostgreSQL database
- HiveMQ MQTT broker
- ESP32 IoT devices
- Water flow sensors
- Solenoid valve control

## Main Objectives Achieved

- Zone-level water monitoring
- Real-time leakage detection
- Automated selective valve shutoff
- User-friendly mobile/web interface
- Cloud-based backend and database integration
- Usage analytics and reports

## Major Engineering Decisions

- FastAPI for asynchronous backend services
- Supabase PostgreSQL for relational data
- MQTT for IoT communication
- Flutter for cross-platform UI
- Background batch processing for performance
- Daily aggregation for efficient analytics
- JWT/OTP/2FA for custom authentication

## Limitations

- Micro-leaks below threshold may not trigger shutoff
- IoT nodes depend on Wi-Fi and power
- Render free tier may introduce cold start delays
- Live dashboard data depends on active ESP32 device

## Future Enhancements

- Machine learning consumption forecasting
- National Water Supply and Drainage Board integration
- GSM module and battery backup
- More advanced alerting and admin features
