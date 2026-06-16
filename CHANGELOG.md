# Changelog

All notable changes to ReceiptSplit are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] — Phase 1: Foundation & Clickable MVP

### Added
- Repository initialized with backend structure
- `pyproject.toml` with full dependency specification
- Alembic migration environment
- Phase 1 schema: rooms, participants, invites, receipts, line items,
  adjustments, assignments, split sessions, participant totals, room events,
  room sequences, receipt edits
- Shared infrastructure: `Paise`, `VPA`, `Nickname`, `Color` value objects
- Shared infrastructure: `DomainError` hierarchy, error codes
- Shared infrastructure: input validators, HTML sanitizer
- Shared infrastructure: injectable clock for testability
- Auth module: capability token generation, hashing, verification
- Auth module: FastAPI dependencies (`require_room_access`, `require_creator_in_room`)

---

*Entries are added to [Unreleased] during development and moved to a versioned
release when the phase milestone test passes.*
