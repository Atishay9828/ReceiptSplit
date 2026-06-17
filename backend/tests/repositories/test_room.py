import pytest
from uuid import uuid4
from sqlalchemy import text

from app.models.room import Room
from app.repositories.postgres.room import PostgresRoomRepository
from app.shared.errors import DomainError


@pytest.mark.asyncio
async def test_room_crud(db_session):
    repo = PostgresRoomRepository()
    
    # Create
    room = Room(status="draft", split_mode="equal")
    await repo.create(db_session, room)
    await db_session.commit()
    
    assert room.id is not None
    
    # Read
    fetched = await repo.get_by_id(db_session, room.id)
    assert fetched is not None
    assert fetched.status == "draft"
    assert fetched.version == 1
    
    # CAS Update success
    updated = await repo.update(db_session, room.id, 1, {"payer_name": "Alice"})
    assert updated is True
    await db_session.commit()
    
    # Read updated
    fetched = await repo.get_by_id(db_session, room.id)
    assert fetched.payer_name == "Alice"
    assert fetched.version == 2
    
    # CAS Update fail (version mismatch)
    updated = await repo.update(db_session, room.id, 1, {"payer_name": "Bob"})
    assert updated is False
    await db_session.commit()
    
    # Not found error
    with pytest.raises(DomainError) as exc:
        await repo.fetch_one(db_session, uuid4())
    assert "ROOM_NOT_FOUND" in exc.value.code
