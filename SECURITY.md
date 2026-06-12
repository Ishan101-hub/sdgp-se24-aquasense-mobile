# Security Policy

AquaSense handles authentication, user data, device control, and IoT communication. Security must be treated as a core system requirement.

## Production Backend

```text
https://sdgp-se24-aquasense-mobile.onrender.com
```

## Sensitive Assets

Never commit:

- `.env`
- Supabase database password
- HiveMQ username/password
- JWT secret
- Gmail SMTP app password
- Firebase service account keys
- Encryption keys

## Authentication Features

The system includes:

- JWT authentication
- OTP verification
- Two-Factor Authentication
- bcrypt password hashing
- Fernet encryption for sensitive values
- Token invalidation / blacklist-based logout

## Reporting Security Issues

Open a private issue or contact the project maintainers directly. Do not disclose exploitable issues publicly until they are fixed.

## Deployment Security Checklist

- [ ] `ENVIRONMENT=production`
- [ ] `CORS_ALLOWED_ORIGINS` only includes approved frontend URLs
- [ ] HTTPS API only
- [ ] Database URL stored in Render environment variables
- [ ] MQTT credentials stored in Render environment variables
- [ ] Firebase config reviewed before public release
