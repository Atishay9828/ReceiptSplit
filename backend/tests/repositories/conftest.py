"""
Fixtures for repository integration tests.

Strategy:
- postgres_container (session, sync): spins up PG once.
- db_url (session, sync): the asyncpg URL.
- _create_tables (session, sync): creates DDL via asyncio.run() + asyncpg.
- async_engine (function, async): fresh engine per test on the test's own event loop.
- db_session (function, async): session inside a rolled-back transaction for isolation.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

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


@pytest.fixture(scope="session", autouse=True)
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
async def async_engine(db_url: str) -> AsyncGenerator[AsyncEngine, None]:
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
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await txn.rollback()
