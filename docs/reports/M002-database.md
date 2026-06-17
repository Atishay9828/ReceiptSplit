# Milestone M002 — Database Schema

## Goal

Define the complete Phase 1 PostgreSQL relational schema as a single Alembic migration that can be applied to a blank database. The schema must fully satisfy the Phase 1 Implementation Design, the Product Decisions Document, and all DB-series amendments from the Phase 1 Design Amendments v1.

---

## Scope

**Included:**
- All 12 Phase 1 tables defined in a single migration `001_phase1_schema.py`
- All primary keys, foreign keys, unique constraints, and check constraints
- All DB-series amendments (DB-1 through DB-5)
- Partial indexes for performance
- `downgrade()` function for clean rollback

**Excluded:**
- SQLAlchemy ORM model classes (declared separately in the repository layer, M005)
- Any seed data or fixtures
- Any views or stored procedures
- Phase 2 tables (OCR pipeline) — not part of Phase 1

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/migrations/versions/001_phase1_schema.py` | Single Alembic migration creating all 12 Phase 1 tables |

## Files Modified

| File | Reason |
|------|--------|
| `backend/migrations/env.py` | Wired to `app.database` async engine metadata |

---

## Architecture Decisions

### Single migration for Phase 1 schema
All 12 tables are created in one migration. This makes the Phase 1 schema atomic — either everything exists or nothing does — and simplifies the initial deployment. Multi-migration splits were considered but rejected as premature decomposition for a greenfield project.

### UUID primary keys with `gen_random_uuid()`
All PK columns use `UUID` with `server_default=gen_random_uuid()`. This avoids sequential ID exposure (enumeration attacks), allows client-side ID pre-generation, and works naturally with distributed systems if needed in future.

### Paise as `BigInteger`, never `NUMERIC`
All monetary columns are `BigInteger` (paise = 1/100 rupee). `NUMERIC(12,2)` was considered and rejected — integer paise avoids float representation issues and aligns with the split engine's integer-only arithmetic. See PDD §5.

### Amendment DB-1 — Atomic per-room sequence via `room_sequences`
The original design used `MAX(sequence_no)+1` to generate `room_events.sequence_no`. Under concurrent writes this creates a race condition where two writers read the same MAX and produce duplicate sequence numbers. Fix: a dedicated `room_sequences` table with one row per room is incremented atomically via `UPDATE room_sequences SET next_seq = next_seq + 1 WHERE room_id = ? RETURNING next_seq` inside the same transaction that writes the event.

### Amendment DB-2 — `UNIQUE(room_id)` on `split_sessions`
Enforces the one-session-per-room invariant at the database layer. A `UNIQUE` constraint is cheaper than an application-level check and survives concurrent racing locks.

### Amendment DB-3 — `receipt_edits` audit trail
An append-only table recording every creator edit to receipt items/adjustments, written in the same transaction as the mutation. Required for future dispute resolution and OCR override tracking.

### Amendment DB-4 — `split_adjustments` replaces hardcoded columns
The original design stored tax, service_charge, discount as separate columns on `receipts`. This was replaced with a generic `split_adjustments` table with a `type` column. This enables multiple tax lines (CGST + SGST), future adjustment types, and matches the split engine's `SplitAdjustment` model exactly.

### Amendment DB-5 — `adjustments_snapshot` JSON on `split_sessions`
At the moment the split is locked, the current adjustment values are snapshotted into a JSON column. This prevents historical split results from changing if adjustments are edited after locking.

### Partial indexes
Three tables use PostgreSQL partial indexes (`WHERE` clause):
- `idx_rooms_status_expires` — only non-terminal rooms (for expiry cron)
- `idx_participants_room` — only active participants (`left_at IS NULL`)
- `idx_items_receipt` — only non-deleted items (`deleted_at IS NULL`)
- `idx_adjustments_room` — only non-deleted adjustments (`deleted_at IS NULL`)

These reduce index size and scan cost for the common query pattern.

### Signed `amount_paise` for `split_adjustments`
The `amount_paise` check constraint allows negative values (`> -10000000`). The `adjustment` type can be negative (OCR reconciliation delta). Tax/fee/discount non-negativity is enforced at the application layer, not the DB, to avoid complicating the constraint.

### `version` column for optimistic locking
`rooms`, `line_items`, `split_adjustments`, and `split_sessions` all have a `version INTEGER` column. The concurrency pattern is `UPDATE ... WHERE id = ? AND version = expected_version`. No row lock is held outside the transaction. See PDD §14.

---

## Implementation Details

### Table dependency order

```
rooms
  ├── room_sequences       (FK: rooms)
  ├── room_invites         (FK: rooms)
  ├── room_events          (FK: rooms)
  ├── room_participants    (FK: rooms, room_invites)
  │     └── receipt_edits  (FK: receipts, room_participants)
  └── receipts             (FK: rooms)
        └── line_items     (FK: receipts)
              └── line_item_assignments (FK: rooms, line_items, room_participants)
  ├── split_adjustments    (FK: rooms)
  └── split_sessions       (FK: rooms)
        └── participant_totals (FK: split_sessions, room_participants)
```

### Room state machine

```
draft → active → settling → settled
  ↓                           ↓
expired                    archived
```

Status enforced by `ck_rooms_status` CHECK constraint and transitions enforced at service layer.

### Tables summary

| Table | Rows represent |
|-------|---------------|
| `rooms` | A bill-splitting session (state machine + version lock) |
| `room_sequences` | Atomic event sequence counter per room (DB-1) |
| `room_invites` | Capability token hashes for join links |
| `room_participants` | All users in a room including creator |
| `receipts` | One receipt per room (manual or OCR source) |
| `line_items` | Individual receipt items (soft-deleted) |
| `split_adjustments` | Taxes, fees, discounts, adjustments (DB-4) |
| `line_item_assignments` | Item-claiming records (item_wise mode) |
| `split_sessions` | Locked split computation snapshots (DB-2, DB-5) |
| `participant_totals` | Per-participant final amounts |
| `room_events` | Append-only event log for real-time |
| `receipt_edits` | Audit trail for creator edits (DB-3) |

---

## Bugs Found During Development

None at this milestone. Amendments DB-1 through DB-5 were identified during the pre-implementation adversarial architecture review and applied before any code was written.

---

## Testing

| Test File | Count | Status |
|-----------|-------|--------|
| (no DB tests in M002 — schema verified via `alembic upgrade head`) | 0 | ✅ Migration runs cleanly |

Migration correctness verified by running `alembic upgrade head` and `alembic downgrade base` against a local PostgreSQL instance.

---

## Git History

| Commit | Message |
|--------|---------|
| `5d49d42` | `chore(repo): initialize repository with project structure and tooling` |

> The database schema was included in the foundation commit. Future milestones will split schema changes into dedicated commits.

---

## Risks / Known Limitations

- No ORM models yet — the schema exists only as a migration. Queries cannot be written until M005 (Repository layer) defines SQLAlchemy models.
- `confidence FLOAT` on `line_items` — OCR confidence score uses float. This is acceptable because confidence is never used in financial arithmetic.
- No row-level security (RLS) — access control is enforced at the service layer via capability tokens. PostgreSQL RLS is not enabled.
- `payer_vpa` and `payer_name` are nullable on `rooms` — the payer sets these when entering their UPI ID. Phase 3 (UPI settlement) will need these to be non-null at `settling` state.

---

## Next Milestone

**M003 — Domain Foundations**
- Objective: Implement pure Python value objects, domain errors, validators, auth token primitives.
- Dependencies: M001, M002.
- Blockers: None.

---

## Updated Progress

```
[x] Repository setup        ← M001
[x] Database schema         ← M002
[ ] Domain foundations
[ ] Split engine
[ ] Repository layer
[ ] Services
[ ] API layer
[ ] Frontend
[ ] Realtime
[ ] Deployment
```

---

## Acceptance Checklist

| Requirement | Status |
|-------------|--------|
| All 12 Phase 1 tables created | ✅ |
| All DB-series amendments applied (DB-1 through DB-5) | ✅ |
| UUID PKs with server-side generation | ✅ |
| All monetary fields as BigInteger (paise) | ✅ |
| Partial indexes for performance | ✅ |
| CHECK constraints for all enum-like columns | ✅ |
| `version` column on all CAS-locked tables | ✅ |
| `downgrade()` function reverses all changes | ✅ |
| Migration runs cleanly: `alembic upgrade head` | ✅ |
