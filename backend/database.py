# # database.py
# # AquaSense — Database engine (SQLAlchemy async, Supabase PostgreSQL)

# from typing import AsyncGenerator
# from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
# from config import settings

# engine = create_async_engine(
#     settings.DATABASE_URL,
#     echo=False,
#     pool_size=5,
#     max_overflow=10,
#     pool_pre_ping=True,
# )

# AsyncSessionLocal = async_sessionmaker(
#     bind=engine,
#     expire_on_commit=False,
#     class_=AsyncSession,
# )

# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with AsyncSessionLocal() as session:
#         yield session



# database.py
# AquaSense — Database engine (SQLAlchemy async, Supabase PostgreSQL)
#
# Fix: MaxClientsInSessionMode crash
#
# Root cause: Supabase uses PgBouncer in Session mode. In Session mode every
# client connection holds one real PostgreSQL connection for its entire lifetime.
# The old config allowed SQLAlchemy to create up to pool_size + max_overflow = 15
# simultaneous connections. Under MQTT bursts (multiple tasks fire at once and all
# miss the empty device cache) SQLAlchemy tried to exceed pool_size by using
# max_overflow — PgBouncer rejected those extra connections.
#
# Fix:
#   • max_overflow = 0  → SQLAlchemy NEVER tries to open more than pool_size
#                         connections. Tasks wait in the pool queue instead of
#                         attempting to create a new physical connection.
#   • pool_size = 3     → Stay well within Supabase free-tier PgBouncer limits.
#                         Pair with _db_semaphore(3) in mqtt_service.py so MQTT
#                         tasks never contend for more than 3 slots.
#   • pool_timeout = 30 → If all 3 slots are busy, wait up to 30 s before raising
#                         TimeoutError. This prevents piling up and gives the
#                         semaphore time to drain the queue.
#   • pool_recycle = 300→ Return connections to the OS after 5 min to avoid
#                         PgBouncer "idle connection" evictions causing surprises.
#   • pool_pre_ping     → Validate the connection is still alive before use,
#                         silently replacing any that were dropped.

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=3,        # Max real connections open at once — match the semaphore
    max_overflow=0,     # NEVER exceed pool_size; tasks wait instead of creating new conns
    pool_timeout=30,    # Wait up to 30 s for a free slot before raising TimeoutError
    pool_recycle=300,   # Recycle connections every 5 min (avoids PgBouncer evictions)
    pool_pre_ping=True, # Silently replace dropped connections before use
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session