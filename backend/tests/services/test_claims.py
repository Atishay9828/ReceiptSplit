import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import hash_token
from app.models.receipt import Receipt
from app.models.room_event import RoomEvent
from app.services.registry import get_item_service, get_participant_service, get_room_service
from app.shared.errors import DomainError

pytestmark = pytest.mark.asyncio


async def test_claim_item_success(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session, split_mode="item_wise")
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(
        db_session, room.id, hash_token(i_token), "Alice", "#FFF"
    )

    item = await item_svc.add_item(
        db_session, receipt.id, room.id, participant.id, "Burger", quantity=2, total_paise=1000
    )

    await item_svc.claim_item(
        db_session,
        room_id=room.id,
        item_id=item.id,
        item_version=item.version,
        participant_id=participant.id,
        claimed_qty=1,
    )

    # Validate claim
    updated_item = await item_svc._item_repo.get(db_session, item.id)
    assert len(updated_item.claims) == 1
    assert updated_item.claims[0]["participant_id"] == str(participant.id)
    assert updated_item.claims[0]["qty"] == 1


async def test_claim_item_quantity_exceeded(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session, split_mode="item_wise")
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(
        db_session, room.id, hash_token(i_token), "Alice", "#FFF"
    )

    item = await item_svc.add_item(
        db_session, receipt.id, room.id, participant.id, "Burger", quantity=1, total_paise=1000
    )

    with pytest.raises(DomainError) as exc:
        await item_svc.claim_item(
            db_session,
            room_id=room.id,
            item_id=item.id,
            item_version=item.version,
            participant_id=participant.id,
            claimed_qty=2,
        )
    assert exc.value.code == "CLAIM_QTY_EXCEEDED"


async def test_unclaim_item_success(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session, split_mode="item_wise")
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(
        db_session, room.id, hash_token(i_token), "Alice", "#FFF"
    )

    item = await item_svc.add_item(
        db_session, receipt.id, room.id, participant.id, "Burger", quantity=1, total_paise=1000
    )

    await item_svc.claim_item(
        db_session,
        room_id=room.id,
        item_id=item.id,
        item_version=item.version,
        participant_id=participant.id,
        claimed_qty=1,
    )

    item = await item_svc._item_repo.get(db_session, item.id)

    await item_svc.unclaim_item(
        db_session,
        room_id=room.id,
        item_id=item.id,
        item_version=item.version,
        participant_id=participant.id,
        claimed_qty=1,
    )

    updated_item = await item_svc._item_repo.get(db_session, item.id)
    assert len(updated_item.claims) == 0


async def test_claim_publishes_event(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session, split_mode="item_wise")
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(
        db_session, room.id, hash_token(i_token), "Alice", "#FFF"
    )

    item = await item_svc.add_item(
        db_session, receipt.id, room.id, participant.id, "Burger", quantity=1, total_paise=1000
    )

    events_before = len((await db_session.execute(select(RoomEvent).where(RoomEvent.room_id == room.id))).scalars().all())
    await db_session.commit()

    await item_svc.claim_item(
        db_session,
        room_id=room.id,
        item_id=item.id,
        item_version=item.version,
        participant_id=participant.id,
        claimed_qty=1,
    )

    events_after = len((await db_session.execute(select(RoomEvent).where(RoomEvent.room_id == room.id))).scalars().all())
    await db_session.commit()
    assert events_after == events_before + 1


async def test_unclaim_publishes_event(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session, split_mode="item_wise")
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(
        db_session, room.id, hash_token(i_token), "Alice", "#FFF"
    )

    item = await item_svc.add_item(
        db_session, receipt.id, room.id, participant.id, "Burger", quantity=1, total_paise=1000
    )

    await item_svc.claim_item(
        db_session,
        room_id=room.id,
        item_id=item.id,
        item_version=item.version,
        participant_id=participant.id,
        claimed_qty=1,
    )

    item = await item_svc._item_repo.get(db_session, item.id)

    events_before = len((await db_session.execute(select(RoomEvent).where(RoomEvent.room_id == room.id))).scalars().all())
    await db_session.commit()

    await item_svc.unclaim_item(
        db_session,
        room_id=room.id,
        item_id=item.id,
        item_version=item.version,
        participant_id=participant.id,
        claimed_qty=1,
    )

    events_after = len((await db_session.execute(select(RoomEvent).where(RoomEvent.room_id == room.id))).scalars().all())
    await db_session.commit()
    assert events_after == events_before + 1
