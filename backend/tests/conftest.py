"""
ReceiptSplit — Test Configuration

Shared fixtures, marks, and helpers for all test suites.
Import order: stdlib → third-party → app (no circular imports).
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

# Import all models so Base.metadata knows every table
import app.models  # noqa: F401
from app.database import Base

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ── Shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def fixed_clock():
    """Returns a FixedClock set to 2026-06-01T12:00:00Z."""
    from datetime import datetime

    from app.shared.clock import FixedClock

    return FixedClock(datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC))


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the entire test session."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:
    """Return the asyncpg-compatible connection URL."""
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )


@pytest.fixture(scope="session")
def _create_tables(db_url: str):
    """Create all tables once at session start using asyncpg (no psycopg2 needed)."""

    async def _setup():
        engine = create_async_engine(db_url, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    async def _teardown():
        engine = create_async_engine(db_url, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


@pytest_asyncio.fixture
async def async_engine(
    db_url: str, _create_tables: None
) -> AsyncGenerator[AsyncEngine, None]:
    """Function-scoped async engine: created fresh per test on the test's own event loop."""
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped session inside a transaction that is rolled back after the test.

    session.flush() writes to the DB (visible within the test) but the outer
    transaction rollback ensures nothing persists between tests.
    """
    async with async_engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        yield session
        await session.close()
        await txn.rollback()
