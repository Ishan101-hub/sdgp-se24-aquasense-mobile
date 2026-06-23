# API Documentation

Base URL:

```text
https://sdgp-se24-aquasense-mobile.onrender.com
```

Health check:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "AquaSense",
  "version": "3.1.0"
}
```

## Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create user account |
| POST | `/auth/login` | Login and receive access token |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout / blacklist token |
| POST | `/auth/forgot-password` | Start password reset flow |
| POST | `/auth/reset-password` | Complete password reset |
| POST | `/auth/2fa/verify-login` | Verify 2FA OTP during login |

## User

| Method | Endpoint | Description |
|---|---|---|
| GET | `/user/profile` | Get current user profile |
| PUT | `/user/update-profile` | Update profile details |
| DELETE | `/user/delete-account` | Delete current account |

## Security

| Method | Endpoint | Description |
|---|---|---|
| GET | `/security/settings` | Get security settings |
| POST | `/security/2fa/enable` | Start 2FA enable flow |
| POST | `/security/2fa/verify-enable` | Verify and enable 2FA |
| POST | `/security/2fa/disable` | Disable 2FA |
| POST | `/security/auto-lock` | Set auto-lock duration |
| POST | `/security/login-alerts` | Toggle login alerts |

## District and Terms

| Method | Endpoint | Description |
|---|---|---|
| GET | `/district/my-district` | Get user's selected district |
| POST | `/district/save` | Save district |
| POST | `/terms/save` | Accept terms and conditions |

## Devices / Zones / Networks

Typical operations include:

- Create network
- Create zone
- Register device
- Retrieve device status
- Open/close valve
- View zone configuration

## Analytics

Typical operations include:

- Live usage data
- Daily summaries
- Monthly usage
- Zone summaries
- Detailed zone analytics
- Leak/event history

## Authenticated Request Example

```dart
final response = await http.get(
  Uri.parse('$baseUrl/user/profile'),
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $token',
  },
);
```

## Production URL Rule

Frontend code must use:

```dart
static const String baseUrl = 'https://sdgp-se24-aquasense-mobile.onrender.com';
```

Never deploy with:

```dart
http://localhost:8000
http://192.168.x.x:8000
```
