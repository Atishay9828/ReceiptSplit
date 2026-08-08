"""
C-3 Claim Race Condition — Concurrency Tests

Validates that concurrent claim_item calls cannot cause over-allocation.
Tests run against real PostgreSQL via Testcontainers with actual HTTP requests.

Finding: C-3 (Claim Race Condition)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import create_app
from tests.api.conftest import dev_jwt

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.concurrency]


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def race_engine(db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Engine for the app's session factory."""
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def verify_engine(db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Independent engine for verification queries."""
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def race_client(
    race_engine: AsyncEngine,
) -> AsyncGenerator[AsyncClient, None]:
    """API client with real commit path (not rollback-wrapped)."""
    app = create_app()
    session_factory = async_sessionmaker(
        bind=race_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session, session.begin():
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_active_itemwise_room(client: AsyncClient) -> dict:
    """Create a room, activate it, and return the full creation response."""
    resp = await client.post("/api/rooms", json={"split_mode": "item_wise"})
    assert resp.status_code == 201
    created = resp.json()
    room_id = created["room"]["id"]
    headers = _bearer(created["creator_token"])

    # Activate
    activate_resp = await client.patch(
        f"/api/rooms/{room_id}",
        json={"version": created["room"]["version"], "status": "active"},
        headers=headers,
    )
    assert activate_resp.status_code == 200
    created["room"] = activate_resp.json()
    return created


async def _add_participant(
    client: AsyncClient, room_id: str, invite_token: str, nickname: str
) -> dict:
    """Join a room and return the join response."""
    resp = await client.post(
        f"/api/rooms/{room_id}/join",
        json={
            "invite_token": invite_token,
            "nickname": nickname,
        },
        headers=_bearer(dev_jwt(f"participant-{nickname}")),
    )
    assert resp.status_code == 201
    return resp.json()


async def _add_item(
    client: AsyncClient, room_id: str, token: str, name: str, quantity: int, total_paise: int
) -> dict:
    """Add a line item and return the item response."""
    resp = await client.post(
        f"/api/rooms/{room_id}/items",
        json={"name": name, "quantity": quantity, "total_paise": total_paise},
        headers=_bearer(token),
    )
    assert resp.status_code == 201
    return resp.json()


async def _claim(
    client: AsyncClient, room_id: str, item_id: str, item_version: int, token: str, qty: int
) -> tuple[int, dict]:
    """Attempt to claim an item. Returns (status_code, response_json)."""
    resp = await client.post(
        f"/api/rooms/{room_id}/items/{item_id}/claim",
        json={"item_version": item_version, "claimed_qty": qty},
        headers=_bearer(token),
    )
    return resp.status_code, resp.json()


# ── C-3 Test: Concurrent claim, quantity=1, 2 claimants ──────────────────────


async def test_concurrent_claim_quantity_1(
    race_client: AsyncClient,
    verify_engine: AsyncEngine,
) -> None:
    """
    Item quantity=1, two participants claim qty=1 concurrently using the
    same item version.

    Expected:
    - Exactly one claim succeeds (201)
    - Exactly one claim fails with VERSION_CONFLICT (409)
    - Final DB state: total claimed quantity = 1
    - No over-allocation
    """
    # Setup
    created = await _create_active_itemwise_room(race_client)
    room_id = created["room"]["id"]
    creator_token = created["creator_token"]
    invite_token = created["invite_token"]

    # Add two participants (creator is already participant #1)
    p2 = await _add_participant(race_client, room_id, invite_token, "Alice")

    # Add item with quantity=1
    item = await _add_item(race_client, room_id, creator_token, "Samosa", 1, 5000)
    item_id = item["id"]
    item_version = item["version"]

    # Concurrent claims — both use the same item version
    results = await asyncio.gather(
        _claim(race_client, room_id, item_id, item_version, creator_token, 1),
        _claim(race_client, room_id, item_id, item_version, p2["participant_token"], 1),
    )

    status_codes = [r[0] for r in results]
    successes = [r for r in results if r[0] == 201]
    conflicts = [r for r in results if r[0] == 409]

    # Assertions
    assert len(successes) == 1, (
        f"C-3 REAL: Expected exactly 1 success, got {len(successes)}. Status codes: {status_codes}"
    )
    assert len(conflicts) == 1, (
        f"C-3 REAL: Expected exactly 1 VERSION_CONFLICT, got {len(conflicts)}. "
        f"Status codes: {status_codes}"
    )

    # Verify final DB state
    async with verify_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COALESCE(SUM(claimed_qty), 0) as total "
                "FROM line_item_assignments WHERE line_item_id = :item_id"
            ),
            {"item_id": item_id},
        )
        total = result.scalar()
        assert total == 1, (
            f"C-3 REAL: Over-allocation detected! Expected total_claimed=1, got {total}"
        )


# ── C-3 Test: Concurrent claim, quantity=2, 3 claimants ──────────────────────


async def test_concurrent_claim_quantity_2(
    race_client: AsyncClient,
    verify_engine: AsyncEngine,
) -> None:
    """
    Item quantity=2, three participants claim qty=1 concurrently using the
    same item version.

    With CAS versioning, only ONE claim can succeed per version (the CAS
    update increments the version). The other two fail with VERSION_CONFLICT.
    This is correct: no over-allocation is possible.

    Expected:
    - Exactly 1 claim succeeds (201)
    - Exactly 2 claims fail with VERSION_CONFLICT (409)
    - Final DB total claimed = 1 (the second claim must retry with new version)
    """
    # Setup
    created = await _create_active_itemwise_room(race_client)
    room_id = created["room"]["id"]
    creator_token = created["creator_token"]
    invite_token = created["invite_token"]

    # Add two more participants (creator is already #1)
    p2 = await _add_participant(race_client, room_id, invite_token, "Bob")
    p3 = await _add_participant(race_client, room_id, invite_token, "Charlie")

    # Add item with quantity=2
    item = await _add_item(race_client, room_id, creator_token, "Paneer Tikka", 2, 30000)
    item_id = item["id"]
    item_version = item["version"]

    # Concurrent claims — all three use the same item version
    results = await asyncio.gather(
        _claim(race_client, room_id, item_id, item_version, creator_token, 1),
        _claim(race_client, room_id, item_id, item_version, p2["participant_token"], 1),
        _claim(race_client, room_id, item_id, item_version, p3["participant_token"], 1),
    )

    status_codes = [r[0] for r in results]
    successes = [r for r in results if r[0] == 201]
    conflicts = [r for r in results if r[0] == 409]

    # With CAS, only 1 of 3 succeeds (the one whose UPDATE matched the version)
    assert len(successes) == 1, (
        f"Expected exactly 1 success, got {len(successes)}. Status codes: {status_codes}"
    )
    assert len(conflicts) == 2, (
        f"Expected exactly 2 conflicts, got {len(conflicts)}. Status codes: {status_codes}"
    )

    # Verify: no over-allocation in DB
    async with verify_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COALESCE(SUM(claimed_qty), 0) as total "
                "FROM line_item_assignments WHERE line_item_id = :item_id"
            ),
            {"item_id": item_id},
        )
        total = result.scalar()
        assert total <= 2, (
            f"C-3 REAL: Over-allocation detected! Expected total_claimed <= 2, got {total}"
        )
        assert total == 1, f"Expected total_claimed=1 (only one CAS winner), got {total}"


# ── Repeated runs for confidence ─────────────────────────────────────────────


@pytest.mark.parametrize("run", range(5))
async def test_concurrent_claim_no_overallocation_repeated(
    race_client: AsyncClient,
    verify_engine: AsyncEngine,
    run: int,
) -> None:
    """
    Repeat the qty=1 race scenario 5 times to increase confidence
    that no over-allocation can occur under contention.
    """
    created = await _create_active_itemwise_room(race_client)
    room_id = created["room"]["id"]
    creator_token = created["creator_token"]
    invite_token = created["invite_token"]

    p2 = await _add_participant(race_client, room_id, invite_token, f"Racer-{run}")

    item = await _add_item(race_client, room_id, creator_token, f"Item-{run}", 1, 10000)
    item_id = item["id"]
    item_version = item["version"]

    results = await asyncio.gather(
        _claim(race_client, room_id, item_id, item_version, creator_token, 1),
        _claim(race_client, room_id, item_id, item_version, p2["participant_token"], 1),
    )

    successes = [r for r in results if r[0] == 201]
    assert len(successes) == 1, f"Run {run}: expected 1 success, got {len(successes)}"

    # Verify DB integrity
    async with verify_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COALESCE(SUM(claimed_qty), 0) as total "
                "FROM line_item_assignments WHERE line_item_id = :item_id"
            ),
            {"item_id": item_id},
        )
        total = result.scalar()
        assert total == 1, f"Run {run}: C-3 REAL — over-allocation! total={total}"
