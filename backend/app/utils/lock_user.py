from datetime import datetime, timezone, timedelta

# How many failed attempts before the account gets locked
MAX_FAILED_ATTEMPTS = 5

# How long the account stays locked in minutes
LOCKOUT_DURATION_MINUTES = 15


async def is_account_locked(email: str) -> tuple[bool, int]:
    from app.database import supabase

    # Find the failed attempts record for this email
    result = supabase.table("failed_attempts").select("*").eq("email", email).execute()

    if not result.data:
        # No failed attempts on record — account is not locked
        return False, 0

    record = result.data[0]
    locked_until = record.get("locked_until")

    if locked_until:
        # Convert string to datetime
        locked_until_dt = datetime.fromisoformat(
            locked_until.replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) < locked_until_dt:
            # Account is still locked — calculate minutes remaining
            remaining = int(
                (locked_until_dt - datetime.now(timezone.utc)).total_seconds() / 60
            ) + 1
            return True, remaining

        # Lockout has expired — reset automatically
        await reset_failed_attempts(email)

    return False, 0


async def record_failed_attempt(email: str):
    from app.database import supabase

    result = supabase.table("failed_attempts").select("*").eq("email", email).execute()

    if not result.data:
        # First failed attempt — create a fresh record
        supabase.table("failed_attempts").insert({
            "email": email,
            "attempts": 1,
            "last_attempt": datetime.now(timezone.utc).isoformat(),
            "locked_until": None
        }).execute()
        return

    record = result.data[0]
    attempts = record.get("attempts", 0) + 1

    if attempts >= MAX_FAILED_ATTEMPTS:
        # Lock the account for 15 minutes
        locked_until = (
            datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        ).isoformat()
        supabase.table("failed_attempts").update({
            "attempts": attempts,
            "last_attempt": datetime.now(timezone.utc).isoformat(),
            "locked_until": locked_until
        }).eq("email", email).execute()
    else:
        # Just increment the counter
        supabase.table("failed_attempts").update({
            "attempts": attempts,
            "last_attempt": datetime.now(timezone.utc).isoformat()
        }).eq("email", email).execute()


async def reset_failed_attempts(email: str):
    from app.database import supabase

    # Called after successful login — wipes the failed attempts record
    supabase.table("failed_attempts").delete().eq("email", email).execute()