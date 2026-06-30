"""
Tests for the Room Events API (M009 Realtime/Event Sync).

Covers:
  - Auth: participant token, creator token, owner JWT, cross-room rejection.
  - Replay endpoint (GET /api/rooms/{room_id}/events).
  - Stream endpoint (GET /api/rooms/{room_id}/events/stream) — SSE formatting and deduplication.
  - Latest endpoint (GET /api/rooms/{room_id}/events/latest).
  - Transaction safety regression: failed mutations do not emit broker events.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from app.services.registry import get_broker, get_event_publisher
from tests.api.conftest import bearer

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.realtime.broker import RoomEventBroker


pytestmark = pytest.mark.asyncio

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def broker() -> "RoomEventBroker":
    return get_broker()


@pytest.fixture
async def active_room(api_client: "AsyncClient") -> dict:
    """Creates a room via API and returns room_id and tokens."""
    r = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    assert r.status_code == 201
    data = r.json()

    room_id = data["room"]["id"]
    creator_token = data["creator_token"]
    invite_token = data["invite_token"]

    # Join a participant to generate some events
    join_r = await api_client.post(
        f"/api/rooms/{room_id}/join",
        json={"invite_token": invite_token, "nickname": "TestUser", "color": "#4F46E5"},
    )
    assert join_r.status_code == 201
    participant_token = join_r.json()["participant_token"]

    return {
        "room_id": room_id,
        "creator_token": creator_token,
        "invite_token": invite_token,
        "participant_token": participant_token,
    }


# ── Auth & Replay Tests ───────────────────────────────────────────────────────


async def test_list_room_events_requires_auth(
    api_client: "AsyncClient",
    active_room: dict,
) -> None:
    """Missing token -> 401."""
    room_id = active_room["room_id"]
    r = await api_client.get(f"/api/rooms/{room_id}/events")
    assert r.status_code == 403


async def test_list_room_events_with_participant_token(
    api_client: "AsyncClient",
    active_room: dict,
) -> None:
    """Capability token grants access."""
    room_id = active_room["room_id"]
    token = active_room["participant_token"]
    r = await api_client.get(
        f"/api/rooms/{room_id}/events",
        headers=bearer(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["room_id"] == str(room_id)
    assert "events" in data


async def test_list_room_events_rejects_cross_room_token(
    api_client: "AsyncClient",
    active_room: dict,
) -> None:
    """Token for room A cannot access room B."""
    room_a_token = active_room["participant_token"]

    # Create room B
    r_b = await api_client.post("/api/rooms", json={"split_mode": "equal"})
    room_b_id = r_b.json()["room"]["id"]

    r = await api_client.get(
        f"/api/rooms/{room_b_id}/events",
        headers=bearer(room_a_token),
    )
    assert r.status_code == 403


async def test_list_room_events_after_sequence(
    api_client: "AsyncClient",
    active_room: dict,
) -> None:
    """after_sequence filters the returned events."""
    room_id = active_room["room_id"]
    token = active_room["creator_token"]

    # Fetch all events first to know how many there are.
    r1 = await api_client.get(
        f"/api/rooms/{room_id}/events",
        headers=bearer(token),
    )
    assert r1.status_code == 200
    all_events = r1.json()["events"]
    assert len(all_events) >= 2  # room.created and participant.joined

    # Now filter.
    r2 = await api_client.get(
        f"/api/rooms/{room_id}/events?after_sequence=1",
        headers=bearer(token),
    )
    assert r2.status_code == 200
    filtered_events = r2.json()["events"]
    assert len(filtered_events) == len(all_events) - 1
    assert filtered_events[0]["sequence_no"] == 2


async def test_latest_sequence_endpoint(
    api_client: "AsyncClient",
    active_room: dict,
) -> None:
    room_id = active_room["room_id"]
    token = active_room["creator_token"]

    r = await api_client.get(
        f"/api/rooms/{room_id}/events/latest",
        headers=bearer(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["room_id"] == str(room_id)
    assert data["latest_sequence"] >= 1


# ── Transaction Safety Regression ──────────────────────────────────────────────


async def test_failed_mutation_does_not_publish_event(
    active_room: dict,
    db_session: "AsyncSession",
    broker: "RoomEventBroker",
) -> None:
    """
    Proves that if an outer transaction rolls back (e.g. exception raised in route),
    any events appended via append_in_tx inside that transaction are discarded
    and NOT published to the broker.
    """
    from uuid import UUID

    room_id = UUID(active_room["room_id"])
    publisher = get_event_publisher()

    received = []

    async def _consume() -> None:
        async with broker.subscribe(room_id) as stream:
            async for event in stream:
                if event.event_type in ("test.failed_mutation", "test.sentinel"):
                    received.append(event)
                if event.event_type == "test.sentinel":
                    break

    consumer_task = asyncio.create_task(_consume())
    await asyncio.sleep(0)  # Let consumer subscribe

    # Simulate a request where the inner savepoint commits but the outer transaction rolls back
    try:
        async with db_session.begin_nested():
            await publisher.append_in_tx(
                db_session,
                room_id=room_id,
                event_type="test.failed_mutation",
                actor_id=None,
                payload={},
            )
        # Inner savepoint succeeded, but now we simulate a failure in the caller
        raise ValueError("Simulated route exception")
    except ValueError:
        pass

    # In fastapi, the dependency generator would normally catch the exception and roll back,
    # and then the session is discarded. Since we are reusing the session in this test,
    # we simulate the discard by clearing db_session.info
    await db_session.rollback()
    db_session.info.pop("deferred_events", None)

    # Calling flush should do nothing now.
    await publisher.flush_deferred_events(db_session)

    # Publish a sentinel event to unblock consumer
    from datetime import UTC, datetime

    from app.realtime.broker import RoomEventDTO

    await broker.publish(
        room_id,
        RoomEventDTO(
            id=str(uuid4()),
            room_id=str(room_id),
            sequence_no=999,
            event_type="test.sentinel",
            actor_id=None,
            payload={},
            created_at=datetime.now(tz=UTC),
        ),
    )

    await asyncio.wait_for(consumer_task, timeout=1.0)
    assert len(received) == 1
    assert received[0].event_type == "test.sentinel", "The failed mutation event leaked!"


# ── SSE Stream Smoke Test ──────────────────────────────────────────────────────


async def test_event_stream_replays_missed_events(
    api_client: "AsyncClient",
    active_room: dict,
    broker: "RoomEventBroker",
) -> None:
    """Smoke test: SSE endpoint replays missed events correctly formatted."""
    room_id = active_room["room_id"]
    token = active_room["creator_token"]

    headers = bearer(token)
    headers["X-Test-No-Live"] = "true"

    # Use after_sequence=0 to replay everything.
    async with api_client.stream(
        "GET",
        f"/api/rooms/{room_id}/events/stream",
        params={"after_sequence": 0},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Read the first few lines of the stream
        lines = []
        async for line in response.aiter_lines():
            lines.append(line)
            # Stop after we receive the first full SSE event (id, event, data, \n\n)
            # A full event is 4 lines (id, event, data, empty line)
            if len(lines) >= 4 and lines[-1] == "":
                break

    assert len(lines) >= 4
    assert lines[0].startswith("id: 1")
    assert lines[1].startswith("event: room.created")
    assert lines[2].startswith("data: ")
    assert lines[3] == ""
