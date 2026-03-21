# app/utils/lock_user.py
# AquaSense — Account lockout helpers
# Kulith's lock_user.py ported from supabase-py → SQLAlchemy AsyncSession.

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

MAX_FAILED_ATTEMPTS    = 5
LOCKOUT_DURATION_MINUTES = 15


async def is_account_locked(identifier: str, db: AsyncSession) -> tuple[bool, int]:
    """
    Returns (is_locked, minutes_remaining).
    Automatically clears an expired lockout.
    """
    from models import FailedAttempt

    result = await db.execute(
        select(FailedAttempt).where(FailedAttempt.identifier == identifier)
    )
    record = result.scalar_one_or_none()

    if not record:
        return False, 0

    if record.locked_until:
        if datetime.now(timezone.utc) < record.locked_until:
            remaining = int(
                (record.locked_until - datetime.now(timezone.utc)).total_seconds() / 60
            ) + 1
            return True, remaining

        # Lockout expired — reset automatically
        await reset_failed_attempts(identifier, db)

    return False, 0


async def record_failed_attempt(identifier: str, db: AsyncSession) -> None:
    """Increments the failed attempt counter. Locks after MAX_FAILED_ATTEMPTS."""
    from models import FailedAttempt

    result = await db.execute(
        select(FailedAttempt).where(FailedAttempt.identifier == identifier)
    )
    record = result.scalar_one_or_none()

    if not record:
        record = FailedAttempt(identifier=identifier, attempts=1)
        db.add(record)
    else:
        record.attempts += 1
        if record.attempts >= MAX_FAILED_ATTEMPTS:
            record.locked_until = (
                datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            )

    await db.commit()


async def reset_failed_attempts(identifier: str, db: AsyncSession) -> None:
    """Clears lockout record after a successful login."""
    from models import FailedAttempt

    await db.execute(
        delete(FailedAttempt).where(FailedAttempt.identifier == identifier)
    )
    await db.commit()
