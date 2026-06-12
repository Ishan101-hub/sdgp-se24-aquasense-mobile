# Changelog

All notable changes to AquaSense are documented here.

## [1.0.0] - Production Demo Release

### Added
- Flutter frontend deployment using Firebase Hosting
- FastAPI backend deployment using Render
- Supabase PostgreSQL integration
- HiveMQ MQTT communication
- ESP32 sensor and valve control workflow
- Real-time water monitoring screens
- Leak detection and alert workflow
- User authentication with JWT
- OTP verification and 2FA support
- Profile, district, terms and security screens
- Usage reports and analytics views
- Repository documentation pack

### Changed
- Production API URL updated to Render backend
- Frontend build configured for Firebase Hosting
- Backend deployment environment configured for cloud database and MQTT broker

### Known Limitations
- Render free-tier cold starts may delay the first request
- ESP32 device must be online for live readings
- Very small leaks below configured threshold may not trigger automatic shutoff
