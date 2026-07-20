> Historical milestone evidence.
> Do not load this file into default working context unless investigating this milestone.
> For current project state, read `docs/ACTIVE_CONTEXT.md` and `docs/MILESTONE_INDEX.md`.

# Milestone M003 — Domain Foundations

## Goal

Implement the pure Python domain layer that all business logic depends on: value objects, domain errors, input validators, authentication token primitives, and the clock abstraction. This layer has zero I/O dependencies and is fully tested in isolation.

---

## Scope

**Included:**
- `Paise`, `VPA`, `Nickname`, `Color` value objects
- 12-colour participant palette
- Domain error hierarchy (all custom exceptions)
- Input validation functions (nickname, VPA, paise, item name, adjustment)
- HTML sanitisation (`strip_html`) for XSS prevention
- Auth token generation, hashing, and verification (32-byte capability tokens)
- FastAPI dependency chain for token-based access control
- `Clock` abstraction for testable time

**Excluded:**
- Database access (M005)
- FastAPI route handlers (M006+)
- Split engine (M004)
- Any request/response schemas

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/shared/__init__.py` | Package marker |
| `backend/app/shared/types.py` | Value objects: `Paise`, `VPA`, `Nickname`, `Color`, `COLOR_PALETTE` |
| `backend/app/shared/errors.py` | Domain error hierarchy — all custom exceptions |
| `backend/app/shared/validators.py` | Input validation functions |
| `backend/app/shared/clock.py` | `Clock` abstraction for deterministic time in tests |
| `backend/app/shared/schemas.py` | Shared Pydantic schema base (for future reuse) |
| `backend/app/auth/__init__.py` | Auth package marker |
| `backend/app/auth/tokens.py` | Token generation, HMAC hashing, verification |
| `backend/app/auth/models.py` | `TokenClaims` dataclass |
| `backend/app/auth/dependencies.py` | FastAPI dependency chain: token → participant |
| `backend/tests/unit/__init__.py` | Unit test package marker |
| `backend/tests/unit/test_types.py` | 45 tests for value objects |
| `backend/tests/unit/test_validators.py` | 40 tests for validation functions |
| `backend/tests/unit/test_tokens.py` | 17 tests for auth token primitives |

## Files Modified

None — all new files.

---

## Architecture Decisions

### `Paise` as the sole money type
All monetary values in the domain and service layer are `Paise(int)`. No `float`, no `Decimal` in the calculation path. `Decimal` is used only in `Paise.to_rupees_decimal()` for display and UPI intent generation. This decision is enforced at the type level — `Paise.__add__` and `__sub__` return `Paise`, preventing accidental float promotion. Reference: PDD §5, Phase 1 Design §3.

### Frozen dataclasses with `__slots__`
All value objects are `@dataclass(frozen=True, slots=True)`. `frozen=True` prevents mutation; `slots=True` reduces memory overhead and speeds attribute access. Value objects are used heavily in allocation loops.

### `strip_html` before any string storage
All user-provided strings (nickname, item name) pass through `strip_html()` before construction of the value object. The function uses `html.unescape` followed by regex tag removal and null byte rejection. This prevents stored XSS if the frontend ever fails to escape output.

### Capability tokens (32-byte, not JWT)
Auth uses 32-byte cryptographically random tokens stored as their SHA-256 hash in the DB. Chosen over JWT because:
- No expiry management complexity (tokens are revoked by setting `revoked_at`)
- No secret rotation risk (each token is a capability, not a claim)
- Simpler to audit (token hash in DB is a direct lookup)
- Matches the PDD §7 design: "share a link → join a room"

Reference: PDD §7, Amendment SEC-1.

### `Clock` abstraction
`app/shared/clock.py` defines a `Clock` class with `now() → datetime`. The service layer always calls `clock.now()` rather than `datetime.utcnow()`. In tests a `FakeClock` is injected, making all time-dependent tests deterministic.

### 12-colour palette
`COLOR_PALETTE` is a fixed tuple of 12 visually distinct, accessible hex colours defined in `types.py`. When a participant joins a room, `pick_available_color()` assigns the next unused colour from the palette in join order. Reference: PDD §Q11.

### Validation at the boundary only
Value objects validate their own post-sanitisation invariants (length, regex). The `validators.py` functions handle the user-input-facing concerns (strip HTML, trim whitespace, run checks, raise domain errors). This keeps the two concerns separate.

---

## Implementation Details

### Value object hierarchy

```
Paise(int)          — money amounts
VPA(str)            — UPI virtual payment address
Nickname(str)       — participant display name (1-30 chars, HTML-stripped)
Color(str)          — hex colour from 12-colour palette
```

### Domain error hierarchy

```
ReceiptSplitError (base)
├── ValidationError
│   ├── InvalidNickname
│   ├── InvalidVPAFormat
│   ├── InvalidAdjustmentAmount
│   └── InvalidItemName
├── NotFoundError
│   ├── RoomNotFound
│   └── ParticipantNotFound
├── AuthError
│   ├── InvalidToken
│   └── TokenRevoked
├── ConflictError
│   ├── RoomAlreadyLocked
│   └── DuplicateAssignment
└── BusinessRuleError
    ├── RoomExpired
    └── InvalidRoomTransition
```

### Auth token flow

```
POST /rooms                   → generate 32-byte token → hash → store in DB
                              → return raw token in response (once only)
                              
GET  /rooms/{id}              → client sends token in header
                              → hash token → lookup in DB → get participant
                              → inject TokenClaims into route handler
```

### Paise arithmetic

```python
Paise(500) + Paise(300)  → Paise(800)
Paise(500) - Paise(300)  → Paise(200)
Paise(500) - Paise(600)  → ValueError (no negative money)
Paise(500).to_rupees_str()  → "₹5.00"
Paise(100000).to_rupees_str()  → "₹1,000.00"   # Indian notation
```

---

## Bugs Found During Development

None.

---

## Testing

| Test File | Count | Status |
|-----------|-------|--------|
| `tests/unit/test_types.py` | 45 | ✅ All passed |
| `tests/unit/test_validators.py` | 40 | ✅ All passed |
| `tests/unit/test_tokens.py` | 17 | ✅ All passed |
| **Total** | **102** | **✅ 0 failures** |

---

## Git History

| Commit | Message |
|--------|---------|
| `d1bf058` | `feat(shared): add value objects, domain errors, validators, and clock` |

---

## Risks / Known Limitations

- `Paise.to_rupees_str()` uses Indian number formatting (`1,00,000`). This is correct for INR display but untested against all edge cases (e.g. values over ₹1 crore).
- `strip_html()` uses a regex-based approach rather than a full HTML parser. This is sufficient for the MVP but would not catch all obscure XSS vectors (e.g. CSS injection).
- `TokenClaims` does not include an expiry timestamp. Token invalidation is by revocation only. A future security hardening pass should consider adding short-lived tokens with refresh.
- The `Clock` abstraction is not yet used in all places — some existing imports call `datetime.utcnow()` directly. This should be cleaned up before the service layer is implemented.

---

## Next Milestone

**M004 — Split Engine**
- Objective: Implement the deterministic 13-step financial calculation pipeline.
- Dependencies: M003 value objects (`Paise`), M002 schema (for `SplitInput` field constraints).
- Blockers: None.

---

## Updated Progress

```
[x] Repository setup        ← M001
[x] Database schema         ← M002
[x] Domain foundations      ← M003
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
| `Paise` value object: non-negative, integer-only, arithmetic | ✅ |
| `VPA` value object: regex validation, 50 char max | ✅ |
| `Nickname` value object: 1-30 chars, HTML stripped | ✅ |
| `Color` value object: palette-constrained | ✅ |
| Full domain error hierarchy | ✅ |
| `strip_html` with null byte rejection | ✅ |
| 32-byte capability token generation and HMAC hashing | ✅ |
| FastAPI dependency chain for token auth | ✅ |
| `Clock` abstraction for testable time | ✅ |
| 102 unit tests passing, 0 failures | ✅ |
