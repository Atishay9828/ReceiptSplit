from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.events import stream_room_events
from app.auth.models import RequestAuthContext
from app.realtime.broker import RoomEventBroker
from app.repositories.postgres.event import PostgresEventRepository


@pytest.mark.asyncio
async def test_stream_releases_database_transaction_before_returning_response() -> None:
    db = AsyncMock(spec=AsyncSession)
    event_repo = MagicMock(spec=PostgresEventRepository)
    event_repo.list_after = AsyncMock(return_value=[])

    response = await stream_room_events(
        room_id=uuid4(),
        after_sequence=0,
        _ctx=MagicMock(spec=RequestAuthContext),
        db=db,
        event_repo=event_repo,
        broker=MagicMock(spec=RoomEventBroker),
        x_test_no_live=True,
    )

    assert response.media_type == "text/event-stream"
    db.rollback.assert_awaited_once_with()
