# Milestone 6 — Service Layer

# Goal

Implement the Service Layer for ReceiptSplit, bridging the API/Controllers with the Repositories and Domain logic. The core objective was to construct robust business transaction orchestration, enforce strict concurrency controls (using CAS), emit audit logs for every user action, broadcast reliable realtime events (via the two-phase outbox pattern), and transition the room lifecycle correctly.

# Scope

**Included:**
- Service interfaces for Room, Participant, Item, Adjustment, and Split Session operations.
- Implementation of `EventPublisher` supporting two-phase commit (TXN-2).
- Injection of system time using an injectable `Clock` protocol.
- Strict room lifecycle isolation via `RoomStateMachine`.
- Advanced concurrency controls across all domain entities using optimistic concurrency (CAS).
- Subcomponents for Split orchestrations (`SplitLockCoordinator`, `SplitSessionBuilder`, `SplitPreviewService`).
- Validation of business invariants directly referencing domain models (e.g. `ClaimValidator`).

**Excluded:**
- Implementation of API Handlers (FastAPI routes) — delayed to Milestone 7.
- Websocket manager/connections (Realtime) — delayed to future milestones.
- Service execution over distributed caches or background tasks.

# Architecture Decisions

### 1. **TXN-2 Two-Phase Events Enforcement**
To prevent a transaction rollback from leaving the frontend with phantom events, we introduced a transactional event outbox. Services use `await event_publisher.append_in_tx(db)` to insert the event payload into the same atomic transaction as the mutation. Once the external transaction commits, `await event_publisher.broadcast()` notifies the async messaging systems (e.g., Redis pub/sub) of the event's sequence numbers.

### 2. **Explicit State Machine for Room Lifecycle**
Room transitions are handled centrally in the `app/domain/room_state_machine.py`. Invalid state transitions raise a specialized `InvalidStateTransition` domain exception. 

### 3. **Split Service Decomposition**
The complexity of locking and calculating splits mandated a refactor. We split `SplitService` into targeted sub-components:
- `SplitLockCoordinator`: Handles idempotency, locking mutations, asserting states, and transactionally persisting a new SplitSession.
- `SplitSessionBuilder`: Takes a snapshot of all receipt items, adjustments, and participant claims, mapping them into the split engine inputs.
- `SplitPreviewService`: Runs hypothetical splits without persisting sessions to allow realtime frontend recalculations.

### 4. **No External Error Leaking**
Services intentionally avoid referencing any presentation-layer models or exceptions (like `HTTPException` or FastAPI status codes). If a version mismatch occurs or validation fails, only pure subclasses of `DomainError` are raised, such as `VersionConflict` or `ClaimQuantityExceeded`.

# Progress Checklist
- [x] Service implementations completed (`RoomService`, `ItemService`, `SplitService`, etc.)
- [x] Unit/Integration testing completed with Testcontainers Postgres
- [x] Two-phase commit integration for event broadcasting (TXN-2)
- [x] Optimistic Locking/CAS applied strictly (TXN-1)
- [x] Dependency injection wired via `registry.py`
- [x] M006 Service Layer milestone completed and verified
