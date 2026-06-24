# firebase_service.py
# AquaSense — Firebase push notification service

import base64
import json
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from config import settings

logger = logging.getLogger("aquasense.firebase")
_initialized = False

def init_firebase():
    global _initialized
    if _initialized:
        return
    try:
        raw_env = settings.FIREBASE_CREDENTIALS_JSON
        if not raw_env:
            raise ValueError("FIREBASE_CREDENTIALS_JSON is empty or not set in settings/environment variables.")

        # Ensure we strip any accidental whitespace/newlines from the env string
        decoded = base64.b64decode(raw_env.strip()).decode("utf-8")
        
        cred_dict = json.loads(decoded)
        cred      = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("Firebase Admin initialized ✓")
    except Exception as e:
        logger.error("Firebase init failed: %s", e)
        # Optional: re-raise if you want the app to hard-fail during startup when config is bad
        # raise e 

async def send_leak_push(fcm_token: str, zone_name: str, zone_id: int) -> bool:
    if not _initialized:
        logger.error("Cannot send push notification: Firebase Admin is not initialized.")
        return False
        
    if not fcm_token:
        return False
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="⚠️ Leak Detected - Valve Closed",
                body=f"A leak was detected in {zone_name}. The valve has been automatically closed.",
            ),
            data={
                "type":             "leak_detected",
                "zone_id":          str(zone_id),
                "target_tab_index": "1",
            },
            token=fcm_token,
        )
        messaging.send(message)
        logger.info("Push sent for zone=%d", zone_id)
        return True
    except Exception as exc:
        logger.error("Push failed token=%s: %s", fcm_token[:12], exc)
        return False