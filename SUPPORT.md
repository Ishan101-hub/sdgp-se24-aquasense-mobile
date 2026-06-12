# Support

For setup or usage issues, check the following first:

1. Backend health endpoint: `/health`
2. Firebase frontend deploy status
3. Render logs
4. Supabase project status
5. HiveMQ broker status
6. Browser DevTools Network tab

## Common Issues

### Login fails
Check that the Flutter API base URL points to the Render backend, not `localhost` or a local IP.

### Backend crashes on startup
Check `DATABASE_URL`, Supabase status, and Render environment variables.

### Live sensor data is missing
Check that the ESP32 is powered on, connected to Wi-Fi, and publishing to HiveMQ.

### First request is slow
Render free instances may spin down after inactivity.
