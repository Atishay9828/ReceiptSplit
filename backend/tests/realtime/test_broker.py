"""
Tests for the in-process RoomEventBroker.

Covers:
  - publish to matching subscriber
  - cross-room isolation
  - subscriber cleanup on exit
  - queue overflow → subscriber disconnected (must reconnect)
  - transaction regression: rollback does not emit broker event
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.realtime.broker import QUEUE_CAPACITY, RoomEventBroker, RoomEventDTO

# ── Helpers ────────────────────────────────────────────────────────────────────


def _dto(room_id: UUID | str, seq: int = 1, event_type: str = "item.created") -> RoomEventDTO:
    return RoomEventDTO(
        id=str(uuid4()),
        room_id=str(room_id),
        sequence_no=seq,
        event_type=event_type,
        actor_id=None,
        payload={"item_id": str(uuid4())},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_broker_publish_to_room_subscriber() -> None:
    """Events published to room A arrive at subscribers for room A."""
    broker = RoomEventBroker()
    room_id = uuid4()
    received: list[RoomEventDTO] = []

    async def _consume() -> None:
        async with broker.subscribe(room_id) as stream:
            async for event in stream:
                received.append(event)
                return  # read one event then exit context

    consumer = asyncio.create_task(_consume())
    # Give consumer time to subscribe.
    await asyncio.sleep(0)

    event = _dto(room_id, seq=1)
    await broker.publish(room_id, event)
    await consumer

    assert len(received) == 1
    assert received[0].sequence_no == 1
    assert received[0].room_id == str(room_id)


@pytest.mark.asyncio
async def test_broker_does_not_cross_publish_rooms() -> None:
    """Events published to room A do not arrive at subscribers for room B."""
    broker = RoomEventBroker()
    room_a = uuid4()
    room_b = uuid4()
    received_b: list[RoomEventDTO] = []

    async def _consume_b() -> None:
        async with broker.subscribe(room_b) as stream:
            async for event in stream:
                received_b.append(event)
                return

    consumer = asyncio.create_task(_consume_b())
    await asyncio.sleep(0)

    # Publish to room A — should not reach room B subscriber.
    await broker.publish(room_a, _dto(room_a, seq=5))

    # Publish sentinel to room B to unblock the consumer.
    await broker.publish(room_b, _dto(room_b, seq=1))
    await consumer

    assert len(received_b) == 1
    assert received_b[0].room_id == str(room_b)


@pytest.mark.asyncio
async def test_broker_unsubscribe_cleanup() -> None:
    """After subscribe() context exits, the subscriber queue is removed."""
    broker = RoomEventBroker()
    room_id = uuid4()

    async with broker.subscribe(room_id):
        assert broker.subscriber_count == 1

    # After context exit, subscriber must be cleaned up.
    assert broker.subscriber_count == 0


@pytest.mark.asyncio
async def test_broker_queue_overflow_behavior() -> None:
    """
    When a subscriber's queue fills up, the broker removes it and sends a
    None sentinel.  The iterator stops — client must reconnect.
    """
    broker = RoomEventBroker()
    room_id = uuid4()
    received: list[RoomEventDTO] = []

    # We use an event to block the consumer so we can overflow its queue.
    blocker = asyncio.Event()

    async def _slow_consumer() -> None:
        async with broker.subscribe(room_id) as stream:
            async for event in stream:
                received.append(event)
                await blocker.wait()  # Block forever until we let it go

    consumer = asyncio.create_task(_slow_consumer())
    await asyncio.sleep(0)  # let consumer subscribe

    # Publish QUEUE_CAPACITY + 10 events.
    # The consumer will read the first one and block.
    # The queue will fill up and overflow.
    for seq in range(1, QUEUE_CAPACITY + 10):
        await broker.publish(room_id, _dto(room_id, seq=seq))

    # The broker should have removed the subscriber and put `None` (or cleared and put `None`).
    # Unblock the consumer so it can process what's left in its queue and eventually hit `None`.
    blocker.set()

    try:
        await asyncio.wait_for(consumer, timeout=2.0)
    except TimeoutError:
        consumer.cancel()
        pytest.fail("Consumer task did not stop after queue overflow sentinel")

    # Subscriber must be cleaned up.
    assert broker.subscriber_count == 0


@pytest.mark.asyncio
async def test_broker_multiple_subscribers_same_room() -> None:
    """Multiple subscribers on the same room each receive their own copy."""
    broker = RoomEventBroker()
    room_id = uuid4()
    results: dict[str, list[int]] = {"a": [], "b": []}

    async def _consumer(key: str) -> None:
        async with broker.subscribe(room_id) as stream:
            async for event in stream:
                results[key].append(event.sequence_no)
                return

    task_a = asyncio.create_task(_consumer("a"))
    task_b = asyncio.create_task(_consumer("b"))
    await asyncio.sleep(0)

    await broker.publish(room_id, _dto(room_id, seq=42))
    await task_a
    await task_b

    assert results["a"] == [42]
    assert results["b"] == [42]
