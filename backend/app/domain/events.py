"""
ReceiptSplit — Event Payload Contracts

Defines the structure of event payloads broadcasted via the two-phase event publisher.
These contracts are used by clients (frontend, realtime subscribers) to reconcile state.

Design authority:
    - PDD §11.1 (Realtime Events)
    - Phase 1 Design Amendments (TXN-2)

Event Types & Payloads:

room.created
    {
        "split_mode": str
    }

room.updated
    {
        "fields": list[str]  # e.g. ["payer_vpa", "split_mode"]
    }

room.state_changed
    {
        "from": str,
        "to": str
    }

participant.joined
    {
        "participant_id": str,
        "nickname": str,
        "color": str
    }

item.created
    {
        "item_id": str,
        "name": str
    }

item.updated
    {
        "item_id": str,
        "fields": list[str]
    }

item.deleted
    {
        "item_id": str,
        "name": str
    }

adjustment.created
    {
        "adjustment_id": str,
        "type": str,
        "label": str
    }

adjustment.updated
    {
        "adjustment_id": str,
        "fields": list[str]
    }

adjustment.deleted
    {
        "adjustment_id": str
    }

claim.created
    {
        "item_id": str,
        "claimed_qty": int,
        "assignment_id": str  # Present in append_in_tx, might not be needed in broadcast but good to have
    }

claim.deleted
    {
        "item_id": str,
        "participant_id": str
    }

split.locked
    {
        "session_id": str,
        "grand_total_paise": int
    }

split.unlocked
    {}  # empty payload
"""
