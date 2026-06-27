"""
C-2 Transaction Ownership — Integration Tests

Validates that `get_db()` + service `async with db.begin()` persists data
correctly in a production-style request lifecycle.

These tests use the real FastAPI app with get_db() overridden to point at the
Testcontainers PostgreSQL database (NOT the rollback-wrapped test session).
Verification queries run on a completely separate connection.

Finding: C-2 (Transaction Ownership)
"""

from __future__ import annotations

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

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def real_engine(db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Separate engine for the real app session factory (not rollback-wrapped)."""
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def verify_engine(db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Completely independent engine for verification queries."""
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def real_api_client(
    real_engine: AsyncEngine,
) -> AsyncGenerator[AsyncClient, None]:
    """
    API client using the real get_db() pattern — NOT the rollback-wrapped
    test session. This tests the actual production commit path.
    """
    app = create_app()
    session_factory = async_sessionmaker(
        bind=real_engine,
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


# ── C-2 Test: Room creation persists all rows ────────────────────────────────


async def test_room_creation_persists_all_rows(
    real_api_client: AsyncClient,
    verify_engine: AsyncEngine,
) -> None:
    """
    POST /api/rooms and verify all 6 entity types persist in the database
    using a completely separate connection.

    Expected rows:
      - rooms
      - receipts
      - room_sequences
      - room_participants (creator)
      - room_invites (creator invite)
      - room_events (room.created)
    """
    # Act: create room via the real app
    response = await real_api_client.post(
        "/api/rooms", json={"split_mode": "equal"}
    )
    assert response.status_code == 201, f"Room creation failed: {response.text}"
    body = response.json()
    room_id = body["room"]["id"]

    # Verify: open a completely new connection and query directly
    async with verify_engine.connect() as conn:
        # 1. Room row
        result = await conn.execute(
            text("SELECT id, status, split_mode FROM rooms WHERE id = :id"),
            {"id": room_id},
        )
        room_row = result.first()
        assert room_row is not None, "C-2 REAL: room row not persisted"
        assert str(room_row.status) == "draft"
        assert str(room_row.split_mode) == "equal"

        # 2. Receipt row
        result = await conn.execute(
            text("SELECT id FROM receipts WHERE room_id = :room_id"),
            {"room_id": room_id},
        )
        receipt_row = result.first()
        assert receipt_row is not None, "C-2 REAL: receipt row not persisted"

        # 3. Room sequence row
        result = await conn.execute(
            text("SELECT room_id, next_seq FROM room_sequences WHERE room_id = :room_id"),
            {"room_id": room_id},
        )
        seq_row = result.first()
        assert seq_row is not None, "C-2 REAL: room_sequence row not persisted"

        # 4. Creator participant row
        result = await conn.execute(
            text(
                "SELECT id, role FROM room_participants "
                "WHERE room_id = :room_id AND role = 'creator'"
            ),
            {"room_id": room_id},
        )
        participant_row = result.first()
        assert participant_row is not None, "C-2 REAL: creator participant not persisted"

        # 5. Invite row
        result = await conn.execute(
            text("SELECT id, type FROM room_invites WHERE room_id = :room_id"),
            {"room_id": room_id},
        )
        invite_row = result.first()
        assert invite_row is not None, "C-2 REAL: invite row not persisted"
        assert str(invite_row.type) == "creator"

        # 6. Room event row (room.created)
        result = await conn.execute(
            text(
                "SELECT id, event_type FROM room_events "
                "WHERE room_id = :room_id AND event_type = 'room.created'"
            ),
            {"room_id": room_id},
        )
        event_row = result.first()
        assert event_row is not None, "C-2 REAL: room.created event not persisted"


# ── C-2 Test: Item creation persists ─────────────────────────────────────────


async def test_item_creation_persists(
    real_api_client: AsyncClient,
    verify_engine: AsyncEngine,
) -> None:
    """
    POST /api/rooms → activate → POST /api/rooms/{id}/items
    Verify the item row persists in a new session.

    This confirms mutation persistence beyond room creation.
    """
    # Step 1: Create room
    create_resp = await real_api_client.post(
        "/api/rooms", json={"split_mode": "equal"}
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    room_id = created["room"]["id"]
    creator_token = created["creator_token"]
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Step 2: Activate room (draft → active)
    activate_resp = await real_api_client.patch(
        f"/api/rooms/{room_id}",
        json={"version": created["room"]["version"], "status": "active"},
        headers=headers,
    )
    assert activate_resp.status_code == 200, f"Activation failed: {activate_resp.text}"
    assert activate_resp.json()["status"] == "active"

    # Step 3: Add item
    item_resp = await real_api_client.post(
        f"/api/rooms/{room_id}/items",
        json={"name": "Masala Dosa", "quantity": 2, "total_paise": 18000},
        headers=headers,
    )
    assert item_resp.status_code == 201, f"Item creation failed: {item_resp.text}"
    item_id = item_resp.json()["id"]

    # Step 4: Verify item exists in a completely new connection
    async with verify_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, name, quantity, total_paise FROM line_items WHERE id = :id"),
            {"id": item_id},
        )
        item_row = result.first()
        assert item_row is not None, "C-2 REAL: item row not persisted after API call"
        assert str(item_row.name) == "Masala Dosa"
        assert item_row.quantity == 2
        assert item_row.total_paise == 18000
"""
Description: These tests use a production-like commit path to verify that data
actually persists after requests complete. If any assertion marked "C-2 REAL"
fails, C-2 is a confirmed issue. If all pass, C-2 is FALSE POSITIVE.
"""
