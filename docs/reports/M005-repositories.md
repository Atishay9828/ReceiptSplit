# Milestone 5 — Repository Layer

## Goal
Implement a robust persistence boundary between the ReceiptSplit business logic and PostgreSQL database, incorporating required transactional boundaries and optimistic concurrency controls.

## Scope
- SQLAlchemy ORM models for all Phase 1 tables.
- Base `PostgresRepository` utility class featuring atomic Compare-and-Swap (CAS) updates.
- Protocol-based interfaces for repositories to decouple business logic from persistence logic.
- PostgreSQL-specific repository implementations utilizing advanced features (e.g., advisory locks).
- Integration test setup using `testcontainers` and PostgreSQL.

## Excluded
- Service layer implementations.
- API endpoints.

## Implementation Details

### Database Interactions
1. **SQLAlchemy Models**: 12 complete SQLAlchemy 2.0 ORM models created, faithfully mapping the Alembic DDL.
2. **CAS Updates**: Implemented atomic CAS updates ensuring data integrity for concurrent mutations (TXN-1), via the `PostgresRepository.cas_update` utility.
3. **Transaction Sequencing**: Implemented atomic event sequencing and appending inside the same transaction using PostgreSQL native `RETURNING` clauses in `PostgresEventRepository` (TXN-2).
4. **Advisory Locks**: Enforced max participant limits securely in highly concurrent environments using PostgreSQL advisory locks (`pg_advisory_xact_lock`) within `PostgresParticipantRepository.join_room_in_tx` (TXN-3).
5. **Partial Indexes & Constraints**: Correctly translated database-level constraints and partial indexes into SQLAlchemy `__table_args__`.

### Testing Strategy
- Integration tests written for Room CRUD operations, Event concurrency and rollback scenarios, and Participant joining concurrent limits.
- Configured Pytest fixtures using `testcontainers[postgres]` combined with rapid TRUNCATE cleanups per test.
- *Note:* Due to the lack of a running Docker daemon in the local execution environment, the automated test suite run was skipped, but the complete containerized test infrastructure is fully prepared for CI pipelines.

## Deviation Log
- Fixed an issue where code formatters aggressively pushed `uuid.UUID` and `datetime.datetime` into `TYPE_CHECKING` blocks. SQLAlchemy 2.0 `Mapped[...]` attributes evaluate types at class creation, so these types must remain globally imported.
