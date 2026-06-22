# Milestone 7 — API Layer

# Goal

Implement the API Layer for ReceiptSplit, providing the external boundary for the frontend to interact with the system. The objective was to expose the existing Service layer through clean RESTful FastAPI endpoints, validate incoming request bodies (schemas), securely scope resources via token-based isolation, map domain errors to appropriate HTTP responses, and maintain full typing and coverage.

# Scope

**Included:**
- FastAPI route implementations under `app/api/routers/` for Rooms, Items, Claims, Participants, Adjustments, and Split workflows.
- Pydantic models for incoming request bodies under `app/api/schemas/`.
- Implementation of dependency injection pipelines for both Auth contexts (`require_room_access`, `require_creator_in_room`) and database sessions (`get_db`).
- A centralized HTTP error handler converting `DomainError` variations to correct status codes (400, 403, 404, 409, 422).
- Route-level dependency enforcement guaranteeing `{room_id}` boundaries are never cross-pollinated (Amendment API-1).
- End-to-end integration tests for all API endpoints under `tests/api/`.

**Excluded:**
- Implementation of `OcrProvider` or the OCR pipeline.
- Websocket manager/connections (Realtime) — delayed to future milestones.
- Frontend implementation.

# Architecture Decisions

### 1. **Resource Isolation with Capability Tokens (API-1)**
To satisfy `API-1`, every endpoint containing `{room_id}` in its path string uses `require_room_access` or `require_creator_in_room`. These dependencies securely fetch the `AuthContext` from the token and perform a strict `if token.room_id != path.room_id` assertion, guaranteeing cross-room tampering is cryptographically impossible.

### 2. **Thin API Handlers**
The FastAPI router logic has been kept entirely devoid of business logic or transaction boundaries. The API's sole responsibility is:
1. Validating auth and dependencies.
2. Resolving services and DB sessions.
3. Invoking `Service` methods.
4. Returning Pydantic-validated responses.

### 3. **Global Domain Error Interception**
Instead of having API endpoints manually `try/except` domain errors to raise `HTTPException`, we implemented a global exception handler mapping for `DomainError` in `app/api/errors.py`. 
For example, `InvalidStateTransition` maps to HTTP 400, `VersionConflict` maps to HTTP 409, `RoomNotFound` maps to HTTP 404, etc.

# Progress Checklist
- [x] Pydantic schemas built (`app/api/schemas/`).
- [x] API routers built (`rooms.py`, `items.py`, `participants.py`, `split.py`, `adjustments.py`).
- [x] Auth dependencies constructed and applied correctly.
- [x] Domain error handling middleware established.
- [x] Endpoint integration testing under `tests/api/`.
- [x] Full regression test suite passing (including Service, Domain, Repository tests).
- [x] `ruff` and `mypy` verifications completed globally.
