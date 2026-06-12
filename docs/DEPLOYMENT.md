# Deployment Guide

AquaSense uses a distributed deployment model.

| Component | Platform |
|---|---|
| Flutter frontend | Firebase Hosting |
| FastAPI backend | Render |
| PostgreSQL database | Supabase |
| MQTT broker | HiveMQ Cloud |
| Version control | GitHub |

## Frontend Deployment: Firebase Hosting

1. Go to frontend directory:

```bash
cd frontend
```

2. Build Flutter web:

```bash
flutter build web --no-wasm-dry-run
```

3. Deploy:

```bash
firebase deploy
```

Live frontend:

```text
https://aquasense-sdgp.web.app
```

## Backend Deployment: Render

Render settings:

| Field | Value |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python run.py` |
| Branch | `main` |

Alternative start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Live backend:

```text
https://sdgp-se24-aquasense-mobile.onrender.com
```

Health check:

```text
https://sdgp-se24-aquasense-mobile.onrender.com/health
```

## Required Render Environment Variables

```env
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://aquasense-sdgp.web.app
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET=...
MQTT_BROKER_HOST=...
MQTT_USERNAME=...
MQTT_PASSWORD=...
EMAIL_USER=...
EMAIL_PASS=...
ENCRYPTION_KEY=...
```

## Supabase Notes

If Supabase is paused due to inactivity, Render startup will fail when the backend tries to verify database tables. Resume the Supabase project and redeploy Render.

## Deployment Checklist

- [ ] `main` branch contains production-ready code
- [ ] Render deploys from `main`
- [ ] Frontend base URL points to Render backend
- [ ] Firebase deployment complete
- [ ] Supabase project resumed and reachable
- [ ] HiveMQ credentials valid
- [ ] `/health` returns `status: ok`
- [ ] Login request goes to Render URL, not localhost

## Common Deployment Errors

### `Application exited early`
Usually caused by missing environment variables, paused Supabase database, invalid database URL, or startup exception.

### `No open ports detected`
Ensure backend binds to `0.0.0.0` and Render's `$PORT`.

### Frontend still calls localhost
Run:

```bash
flutter clean
flutter build web --no-wasm-dry-run
firebase deploy
```

Then hard refresh the browser.
