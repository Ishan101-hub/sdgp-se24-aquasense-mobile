# Repository Setup Instructions

Use this checklist to make the repository portfolio-ready.

## 1. Copy Documentation Pack

Copy these generated files into the root of your AquaSense repository.

## 2. Check Secret Safety

Before pushing publicly, run:

```bash
git grep -n "DATABASE_URL\|JWT_SECRET\|MQTT_PASSWORD\|EMAIL_PASS\|localhost:8000\|192.168"
```

Remove real secrets and local URLs.

## 3. Make Main Production Branch

```bash
git checkout dev
git pull origin dev

git checkout main
git reset --hard dev
git push origin main --force
```

## 4. Set Render Branch to Main

Render Dashboard → Service → Settings → Build & Deploy → Branch → `main`

Then:

```text
Manual Deploy → Deploy latest commit
```

## 5. Deploy Firebase

```bash
cd frontend
flutter build web --no-wasm-dry-run
firebase deploy
```

## 6. Verify Live System

- Frontend loads
- Backend `/health` works
- Login request points to Render URL
- Supabase is active
- MQTT broker connects

## 7. Add Screenshots

Replace generated page screenshots with clean app screenshots if possible.

## 8. Create GitHub Release

Suggested release tag:

```text
v1.0.0-production-demo
```
