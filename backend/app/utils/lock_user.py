from datetime import datetime, timezone, timedelta
from app.database import failed_attempts_collection

# How many failed attempts before the account gets locked
MAX_FAILED_ATTEMPTS = 5

# How long the account stays locked in minutes
LOCKOUT_DURATION_MINUTES = 15


async def get_failed_attempts(email: str) -> dict:
    # Find the failed attempts record for this email
    record = await failed_attempts_collection.find_one({"email": email})
    return record


async def is_account_locked(email: str) -> tuple[bool, int]:
    record = await get_failed_attempts(email)

    if not record:
        # No failed attempts on record — account is not locked
        return False, 0

    locked_until = record.get("locked_until")

    if locked_until:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) < locked_until:
            # Account is still locked — calculate minutes remaining
            remaining = (locked_until - datetime.now(timezone.utc)).seconds // 60
            return True, remaining

        # Lockout has expired — reset automatically
        await reset_failed_attempts(email)

    return False, 0


async def record_failed_attempt(email: str):
    record = await get_failed_attempts(email)

    if not record:
        # First failed attempt — create a fresh record
        await failed_attempts_collection.insert_one({
            "email": email,
            "attempts": 1,
            "last_attempt": datetime.now(timezone.utc),
            "locked_until": None
        })
        return

    attempts = record.get("attempts", 0) + 1

    if attempts >= MAX_FAILED_ATTEMPTS:
        # Lock the account for 15 minutes
        locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        await failed_attempts_collection.update_one(
            {"email": email},
            {"$set": {
                "attempts": attempts,
                "last_attempt": datetime.now(timezone.utc),
                "locked_until": locked_until
            }}
        )
    else:
        # Just increment the counter
        await failed_attempts_collection.update_one(
            {"email": email},
            {"$set": {
                "attempts": attempts,
                "last_attempt": datetime.now(timezone.utc)
            }}
        )


async def reset_failed_attempts(email: str):
    # Called after successful login — wipes the failed attempts record
    await failed_attempts_collection.delete_one({"email": email})