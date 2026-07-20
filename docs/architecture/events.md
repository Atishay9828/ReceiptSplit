# Room Event Synchronization Architecture

ReceiptSplit is a real-time, multi-user bill splitting application. To support offline capabilities, conflict resolution, and real-time collaboration, we use an event-sourcing pattern for mutations combined with an in-process broker for Server-Sent Events (SSE).

## 1. Durable Events (`room_events`)
All domain mutations that affect room state (e.g., item creation, adjustment, participant join) emit a `RoomEvent`. 
- **Durability First**: Events are inserted into the PostgreSQL `room_events` table *before* they are broadcast to connected clients.
- **Strict Ordering**: Events within a room are strictly ordered by a monotonic `sequence_no`. This counter is managed per-room in the `room_sequences` table to avoid global locks.
- **Source of Truth**: The `room_events` table serves as the definitive log of everything that has occurred in a room. 

## 2. Real-time Broker (`RoomEventBroker`)
For real-time delivery, we maintain a lightweight, in-process `RoomEventBroker` using `asyncio.Queue`s.

- **Per-Subscriber Queues**: Each connected SSE client receives its own queue.
- **Queue Limits & Disconnects**: To protect backend memory, queues are bounded to 256 events. If a client is too slow and its queue overflows, the broker forcefully disconnects that subscriber. The client must then reconnect and fetch missed events via the replay endpoint.
- **In-process limitations**: Currently, the broker only broadcasts to clients connected to the same server process. To scale horizontally, this broker will need to be backed by a pub/sub system like Redis or NATS.

## 3. SSE Stream and Replay (`/api/rooms/{room_id}/events/stream`)
The SSE stream endpoint provides robust state synchronization through a "subscribe-first, then replay" strategy:

1. **Subscribe**: The endpoint first subscribes to the `RoomEventBroker`. This ensures no live events are missed during the next step.
2. **Replay**: It queries the `room_events` table for all events with a `sequence_no` greater than the client's requested `after_sequence` and sends them.
3. **Stream Live**: It begins streaming events from the broker.
4. **Deduplication**: Because an event might be retrieved both from the DB replay and from the live broker, the endpoint tracks sent `sequence_no`s and deduplicates on the fly.

## 4. Two-Phase Commit with `EventPublisher`
To ensure clients never receive an event for a mutation that was rolled back:
- **Phase 1 (Transaction)**: `EventPublisher.append_in_tx` inserts the row and stores the resulting event DTO inside the SQLAlchemy session's `info` dictionary (e.g., `db.info["deferred_events"]`).
- **Phase 2 (Post-Commit)**: After the FastAPI dependency successfully commits the transaction, it calls `flush_deferred_events`. This takes the deferred events and publishes them to the broker. If the transaction rolls back, `db.info` is discarded and no broker event is emitted.

## 5. Event Authentication
Events are highly sensitive. Access requires explicit authorization via a combined dependency (`require_room_event_access`):
- Participant Capability Token
- Creator Capability Token
- Room Owner JWT

Cross-room tokens are strictly rejected.
