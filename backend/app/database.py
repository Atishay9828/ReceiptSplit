"""
ReceiptSplit — Async Database Engine & Session Factory

Provides:
  - `engine`         : AsyncEngine (shared, created once at startup)
  - `AsyncSessionLocal` : sessionmaker for async sessions
  - `get_db()`       : FastAPI dependency yielding a per-request session

All database access in the application goes through `get_db()`.
Migrations use a synchronous engine configured in alembic/env.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ── SQLAlchemy base class for all ORM models ──────────────────────────────────

class Base(DeclarativeBase):
    """
    Shared declarative base.  All ORM table models inherit from this.

    Convention:
      - Table names: snake_case plural  (e.g. `rooms`, `room_participants`)
      - Primary keys: UUID via gen_random_uuid()
      - Money columns: BIGINT (paise)
      - Timestamps: TIMESTAMPTZ
    """


# ── Engine ────────────────────────────────────────────────────────────────────

def _build_engine() -> AsyncEngine:
    """
    Creates the async SQLAlchemy engine from settings.

    Pool settings are tuned for a single-instance FastAPI server:
      - pool_size=10: handles moderate concurrency without overwhelming Supabase
      - max_overflow=20: allows burst headroom
      - pool_pre_ping=True: validates connections before checkout (handles
        Supabase's idle connection timeouts)
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.is_development,   # log SQL in development only
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        # Supabase Postgres closes idle connections after ~5 minutes.
        # pool_recycle ensures connections are refreshed before that.
        pool_recycle=300,
    )


engine: AsyncEngine = _build_engine()


# ── Session factory ───────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # objects remain accessible after commit
    autoflush=False,          # explicit flush control in service layer
    autocommit=False,
)


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a per-request async database session.

    Usage:
        @router.get("/example")
        async def handler(db: AsyncSession = Depends(get_db)):
            ...

    The session is closed automatically after the request completes,
    whether or not an exception was raised.  The caller is responsible
    for managing transactions (begin/commit/rollback).
    """
    async with AsyncSessionLocal() as session:
        yield session
