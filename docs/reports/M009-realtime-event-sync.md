# M009 Realtime / Event Sync

## Objective
Implement ReceiptSplit’s backend realtime/event synchronization layer to make room collaboration reliable and frontend-ready.

## Work Completed

1. **In-Process Broker (`RoomEventBroker`)**
   - Implemented an `asyncio.Queue` based in-process broker for Server-Sent Events (SSE).
   - Designed with a strict queue capacity (256 events). If a connected client cannot consume events fast enough, they are forcefully disconnected rather than silently missing events.
   - Implemented complete cross-room isolation at the broker level.

2. **Durable Events & Event Publisher**
   - The `room_events` table remains the absolute source of truth.
   - Refactored `EventPublisher` to follow a strict two-phase commit:
     - **Phase 1**: Insert the event into `room_events` within the current transaction (savepoint) and capture the full generated row (`RETURNING id, created_at`). The DTO is stored in the SQLAlchemy session (`db.info`).
     - **Phase 2**: After the outer transaction commits, the FastAPI dependency (`get_db`) flushes the deferred events to the in-process broker.
   - Built a regression test `test_failed_mutation_does_not_publish_event` to prove that if an outer transaction rolls back, no events are published to the broker.

3. **API Endpoints**
   - `GET /api/rooms/{room_id}/events` - Fetches all durable events after a given `sequence_no`.
   - `GET /api/rooms/{room_id}/events/latest` - Returns the current maximum sequence number for a room.
   - `GET /api/rooms/{room_id}/events/stream` - The SSE stream endpoint. It implements a robust "subscribe-first, then replay, then stream" strategy, deduplicating by `sequence_no` to guarantee zero missed events during the handoff.

4. **Event Authorization**
   - Implemented a unified dependency `require_room_event_access` which validates event endpoint access.
   - Authorized actors include: Participant capability tokens, Creator capability tokens, and Owner JWTs.
   - Cross-room tokens are strictly rejected.

5. **Testing**
   - Full test suite added to cover broker behavior, repository isolation, and the SSE/API endpoints.
   - Suite verified to maintain complete backward compatibility with M007.6 and M008 functionality.

## Deviations from Plan
- `tests.factories` did not exist; I updated `test_events_api.py` to use `api_client` for room creation via the existing endpoints.
- Minor linter updates (`contextlib.suppress`) applied per Ruff's strict guidelines.

## Next Steps
The backend is now prepared for full real-time collaboration. The next milestone should cover OCR processing or frontend scaffolding.
