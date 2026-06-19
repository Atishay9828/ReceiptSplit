import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import hash_token
from app.models.receipt import Receipt
from app.models.receipt_edit import ReceiptEdit
from app.services.registry import get_item_service, get_room_service, get_participant_service

pytestmark = pytest.mark.asyncio


async def test_item_edit_creates_audit_row(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session)
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(db_session, room.id, hash_token(i_token), "Alice", "#FFF")

    # Add item
    item = await item_svc.add_item(
        db_session,
        receipt_id=receipt.id,
        room_id=room.id,
        actor_id=participant.id,
        name="Burger",
        quantity=1,
        total_paise=1000,
    )
    
    # Edit item
    await item_svc.update_item(
        db_session,
        item_id=item.id,
        room_id=room.id,
        receipt_id=receipt.id,
        expected_version=item.version,
        actor_id=participant.id,
        changes={"name": "Cheese Burger", "total_paise": 1500},
    )

    # Check audit rows
    edits = (await db_session.execute(select(ReceiptEdit).where(ReceiptEdit.receipt_id == receipt.id))).scalars().all()
    await db_session.commit()
    # 1 for create, 2 for the 2 updated fields
    assert len(edits) == 3
    
    edit_fields = [e.field for e in edits]
    assert "item.name" in edit_fields
    assert "item.total_paise" in edit_fields


async def test_item_delete_creates_audit_row(db_session: AsyncSession):
    room_svc = get_room_service()
    item_svc = get_item_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session)
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(db_session, room.id, hash_token(i_token), "Alice", "#FFF")

    item = await item_svc.add_item(
        db_session,
        receipt_id=receipt.id,
        room_id=room.id,
        actor_id=participant.id,
        name="Fries",
        quantity=1,
        total_paise=500,
    )

    await item_svc.delete_item(
        db_session,
        item_id=item.id,
        room_id=room.id,
        receipt_id=receipt.id,
        expected_version=item.version,
        actor_id=participant.id,
    )

    edits = (await db_session.execute(select(ReceiptEdit).where(ReceiptEdit.receipt_id == receipt.id))).scalars().all()
    await db_session.commit()
    # 1 for create, 1 for delete
    assert len(edits) == 2
    assert any(e.field == "item.deleted" for e in edits)
