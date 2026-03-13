# database.py
# AquaSense v3 — Database engine and session factory

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

# ── Async engine ──────────────────────────────────────────────
# echo=True logs every SQL statement — useful during development.
# Set echo=False in production to avoid log noise.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    # Pool settings suitable for a single-server FastAPI deployment.
    # Supabase free tier has a max of 20 connections — stay well under it.
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # test connections before use (handles Supabase timeouts)
)

# ── Session factory ───────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# ── NOTE: Base is defined in models.py ───────────────────────
# Do NOT declare Base here. models.py owns Base(DeclarativeBase).
# main.py imports it directly:
#   from models import Base
#   async with engine.begin() as conn:
#       await conn.run_sync(Base.metadata.create_all)
#
# Having two separate Base instances (one here, one in models.py)
# would cause Base.metadata.create_all to see zero tables.

# ── FastAPI dependency ────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession for use in FastAPI route dependencies.
    Session is automatically closed when the request finishes.

    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session