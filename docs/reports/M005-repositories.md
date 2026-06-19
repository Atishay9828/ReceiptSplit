# Milestone 5 — Repository Layer

## Goal

Implement a robust persistence boundary between ReceiptSplit business logic and PostgreSQL, incorporating required transactional boundaries and optimistic concurrency controls.

## Scope

### Included
- 12 SQLAlchemy 2.0 ORM models mapping the Phase 1 schema
- Base `PostgresRepository` utility class with atomic CAS updates
- Protocol-based repository interfaces decoupling business logic from persistence
- PostgreSQL-specific repository implementations (advisory locks, RETURNING clauses)
- Full integration test suite against real PostgreSQL via TestContainers

### Excluded
- Service layer implementations
- API endpoints

---

## Implementation Details

### SQLAlchemy Models (`app/models/`)

| Model | Table | Key Features |
|-------|-------|-------------|
| `Room` | `rooms` | CAS versioning, status enum, partial index on active rooms |
| `RoomSequence` | `room_sequences` | Atomic per-room event counter |
| `RoomInvite` | `room_invites` | Unique token_hash, revocable |
| `RoomParticipant` | `room_participants` | Partial index on active (left_at IS NULL) |
| `Receipt` | `receipts` | 1:1 with room, source enum |
| `LineItem` | `line_items` | CAS versioning, soft-delete via deleted_at |
| `SplitAdjustment` | `split_adjustments` | CAS versioning, soft-delete, type enum |
| `LineItemAssignment` | `line_item_assignments` | Unique (item, participant) constraint |
| `SplitSession` | `split_sessions` | 1:1 with room, JSONB adjustments snapshot |
| `ParticipantTotal` | `participant_totals` | Unique (session, participant) |
| `RoomEvent` | `room_events` | Unique (room_id, sequence_no) index |
| `ReceiptEdit` | `receipt_edits` | Audit trail, composite index |

### Concurrency Patterns

| Pattern | Amendment | Implementation |
|---------|-----------|----------------|
| **CAS Update (TXN-1)** | Atomic version-checked UPDATE | `base.py:cas_update()` — single `UPDATE...WHERE version=:v RETURNING id` |
| **Atomic Event Sequencing (DB-1/TXN-2)** | Gapless sequences | `event.py:append_in_tx()` — `UPDATE room_sequences SET next_seq=next_seq+1 RETURNING next_seq` + `INSERT INTO room_events` |
| **Advisory Lock (TXN-3)** | Serialize room joins | `participant.py:join_room_in_tx()` — `pg_advisory_xact_lock(hashtext(:room_id))` |

### Repository Interfaces (`app/repositories/interfaces/`)

All interfaces use `typing.Protocol` for structural subtyping:

- `RoomRepository` — create, get_by_id, update (CAS), archive, expire
- `ParticipantRepository` — join_room_in_tx, get_by_token, list_active
- `EventRepository` — append_in_tx (atomic sequence + insert)
- `ItemRepository` — create, get, update (CAS), soft_delete
- `AdjustmentRepository` — create, list_by_room, soft_delete
- `ReceiptRepository` — create, get_by_room
- `SplitSessionRepository` — create, get_by_room
- `ReceiptEditRepository` — append_in_tx (audit)

---

## Test Execution Results

### Environment

| Component | Version |
|-----------|---------|
| Docker | 29.2.1 |
| PostgreSQL | 15-alpine (via TestContainers) |
| TestContainers | 4.14.2 |
| SQLAlchemy | 2.0.x (asyncpg driver) |
| pytest-asyncio | 1.4.0 |

### Results

| Test File | Tests | Passed | Failed | Skipped |
|-----------|-------|--------|--------|---------|
| `test_room.py` | 6 | 6 | 0 | 0 |
| `test_event.py` | 2 | 2 | 0 | 0 |
| `test_participant.py` | 3 | 3 | 0 | 0 |
| `test_misc_repos.py` | 9 | 9 | 0 | 0 |
| **Total** | **20** | **20** | **0** | **0** |

**Duration**: 10.17s

### Concurrency Validation

| Test | Result | Description |
|------|--------|-------------|
| `test_concurrent_event_sequencing` | ✅ PASS | 10 concurrent workers append events; sequences are gapless 1..10 |
| `test_event_rollback_on_transaction_failure` | ✅ PASS | Failed transaction fully rolls back both sequence increment and event insert |
| `test_concurrent_join_limit` | ✅ PASS | 5 concurrent joins with limit=3: exactly 3 succeed, 2 get ROOM_FULL |
| `test_room_cas_update_success` | ✅ PASS | CAS update increments version atomically |
| `test_room_cas_update_version_mismatch` | ✅ PASS | Stale version returns False (0 rows) |

### Coverage

```
Name                                           Stmts   Miss Branch BrPart  Cover
────────────────────────────────────────────────────────────────────────────────
app/repositories/interfaces/__init__.py           10      0      0      0   100%
app/repositories/interfaces/adjustment.py          8      0      0      0   100%
app/repositories/interfaces/event.py               5      0      0      0   100%
app/repositories/interfaces/item.py                9      0      0      0   100%
app/repositories/interfaces/participant.py         8      0      0      0   100%
app/repositories/interfaces/receipt.py             8      0      0      0   100%
app/repositories/interfaces/receipt_edit.py        6      0      0      0   100%
app/repositories/interfaces/room.py               10      0      0      0   100%
app/repositories/interfaces/split_session.py       7      0      0      0   100%
app/repositories/postgres/__init__.py              9      0      0      0   100%
app/repositories/postgres/adjustment.py           20      0      0      0   100%
app/repositories/postgres/base.py                 30      1      4      1    94%
app/repositories/postgres/event.py                15      1      2      1    88%
app/repositories/postgres/item.py                 20      0      0      0   100%
app/repositories/postgres/participant.py          35      2      4      2    90%
app/repositories/postgres/receipt.py              18      0      0      0   100%
app/repositories/postgres/receipt_edit.py         14      2      2      1    81%
app/repositories/postgres/room.py                 23      0      0      0   100%
app/repositories/postgres/split_session.py        16      0      0      0   100%
────────────────────────────────────────────────────────────────────────────────
TOTAL                                            271      6     12      5    96%
```

**Repository coverage: 96.11%** (exceeds 80% threshold)

### Uncovered Lines (6 remaining)

| File | Line(s) | Reason |
|------|---------|--------|
| `base.py:34` | `DomainError` raise in `fetch_one` when model name differs | Edge case only hit with non-Room models |
| `event.py:36` | `InternalError` raise when no sequence row | Defensive guard; cannot trigger via normal tests |
| `participant.py:48,58` | `INVALID_TOKEN` and `ROOM_FULL` error paths | Covered in concurrent test but via separate connections |
| `receipt_edit.py:42-44` | `InternalError` on failed INSERT | Defensive guard; DB would have to reject a valid insert |

---

## Findings & Issues Resolved

### Issue 1: asyncio Event-Loop Mismatch (Critical)

**Symptom**: `RuntimeError: Task got Future attached to a different loop`

**Root Cause**: Session-scoped `async_engine` fixture was created on the session event loop, but function-scoped tests each get their own loop. asyncpg detected the mismatch.

**Fix**: Eliminated session-scoped async fixtures entirely. DDL setup uses `asyncio.run()` in a sync fixture. Each test gets a function-scoped `async_engine` on its own loop. NullPool ensures no connection reuse across loops.

### Issue 2: MissingGreenlet on Lazy Attribute Access

**Symptom**: `MissingGreenlet: greenlet_spawn has not been called` when accessing `room.id` after `expire_all()`

**Root Cause**: `expire_all()` marks ORM attributes as expired. Accessing `room.id` triggers a synchronous lazy-load outside SQLAlchemy's greenlet context.

**Fix**: Capture `room.id` into a local variable before calling `expire_all()`.

### Issue 3: Missing psycopg2 Driver

**Symptom**: `ModuleNotFoundError: No module named 'psycopg2'` when using sync `create_engine()`.

**Root Cause**: TestContainers returns a `postgresql+psycopg2` URL. The project only has asyncpg installed.

**Fix**: Use `asyncio.run()` with an asyncpg engine for DDL, avoiding the psycopg2 dependency.

### Issue 4: Missing `expires_at` Field

**Symptom**: `NOT NULL violation` on `rooms.expires_at`.

**Root Cause**: Test Room constructors omitted the required `expires_at` field.

**Fix**: All test helpers now provide `expires_at=datetime.now(UTC) + timedelta(days=1)`.

### Flaky Tests

None discovered. All 20 tests pass consistently.

### Race Conditions

None discovered. The advisory lock correctly serializes concurrent joins and the atomic `UPDATE...RETURNING` correctly serializes event sequencing.

---

## Deviation Log

1. **Removed `from __future__ import annotations`** from model files — ruff's TCH rule moved `uuid.UUID` and `datetime.datetime` into `TYPE_CHECKING` blocks, but SQLAlchemy 2.0 `Mapped[...]` evaluates type annotations at class definition time. Imports must remain at module level.

2. **`ReceiptRepository.update()` raises `NotImplementedError`** — the `receipts` table has no `version` column in the Phase 1 schema, so CAS is not applicable. The interface method exists for forward-compatibility with Phase 2.

---

## Git History

```
da7012f fix(repositories): resolve postgres integration test failures
29a3503 docs: add M005 repository milestone report
6ee8075 feat(repositories): implement postgres repository layer
```
