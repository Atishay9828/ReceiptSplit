import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import hash_token
from app.models.receipt import Receipt
from app.models.receipt_edit import ReceiptEdit
from app.services.registry import get_adjustment_service, get_participant_service, get_room_service

pytestmark = pytest.mark.asyncio


async def test_adjustment_edit_creates_audit_row(db_session: AsyncSession):
    room_svc = get_room_service()
    adj_svc = get_adjustment_service()
    part_svc = get_participant_service()

    room, _, i_token = await room_svc.create_room(db_session)
    receipt = (await db_session.execute(select(Receipt).where(Receipt.room_id == room.id))).scalars().first()
    await db_session.commit()

    participant, _ = await part_svc.join_room(db_session, room.id, hash_token(i_token), "Alice", "#FFF")

    # Add adjustment
    adj = await adj_svc.add_adjustment(
        db_session,
        receipt_id=receipt.id,
        room_id=room.id,
        actor_id=participant.id,
        adj_type="tax",
        label="Service Tax",
        amount_paise=500,
    )

    # Edit adjustment
    await adj_svc.update_adjustment(
        db_session,
        adjustment_id=adj.id,
        room_id=room.id,
        receipt_id=receipt.id,
        expected_version=adj.version,
        actor_id=participant.id,
        changes={"label": "State Tax", "amount_paise": 600},
    )

    # Check audit rows
    edits = (await db_session.execute(select(ReceiptEdit).where(ReceiptEdit.receipt_id == receipt.id))).scalars().all()
    await db_session.commit()
    # 1 for create, 2 for the 2 updated fields
    assert len(edits) == 3

    edit_fields = [e.field for e in edits]
    assert "adjustment.label" in edit_fields
    assert "adjustment.amount_paise" in edit_fields
