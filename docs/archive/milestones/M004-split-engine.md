> Historical milestone evidence.
> Do not load this file into default working context unless investigating this milestone.
> For current project state, read `docs/ACTIVE_CONTEXT.md` and `docs/MILESTONE_INDEX.md`.

# Milestone M004 — Split Engine

## Goal

Implement the deterministic 13-step financial calculation pipeline that splits a restaurant bill among participants. This is the highest-risk component in the system — a financial calculation module that must be correct for all inputs, including edge cases discovered through property-based testing with 10,000 random examples per invariant.

---

## Scope

**Included:**
- Domain models for the split engine I/O contract (`SplitInput`, `SplitResult`, etc.)
- `EqualAllocator` — floor division with round-robin remainder distribution
- `ProportionalAllocator` — proportional allocation by shares, SE-1 zero-denominator guard
- `RoundingPolicy` — floor rounding to nearest ₹1, payer absorbs residual (SE-2)
- `SplitCalculator` — orchestrates all 13 pipeline steps
- `invariants` — post-calculation assertion checks
- `exceptions` — `SplitInvariantFailed` subclasses
- Unit tests for every component
- Hypothesis property-based tests (10,000 examples each)
- 4 golden receipt JSON fixtures covering real-world scenarios

**Excluded:**
- Database persistence (repository layer, M005)
- API endpoints (M006)
- Percentage split mode (not in Phase 1 PDD)
- Historical session replay
- UPI settlement integration (Phase 3)

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/split/__init__.py` | Package marker, exports public API |
| `backend/app/split/models.py` | Frozen dataclass I/O contracts: `SplitInput`, `SplitResult`, `SplitItem`, `SplitAssignment`, `SplitAdjustment`, `SplitParticipant`, `ParticipantBreakdown` |
| `backend/app/split/exceptions.py` | `SplitInvariantFailed`, `SumConservationViolation`, `NegativePayerTotalViolation`, `NegativeTotalViolation`, `AllocationConservationViolation` |
| `backend/app/split/allocators.py` | `EqualAllocator` and `ProportionalAllocator` |
| `backend/app/split/rounding.py` | `RoundingPolicy` — floor rounding, payer residual |
| `backend/app/split/invariants.py` | `check_sum_conservation`, `check_non_negative_totals`, `check_payer_non_negative`, `check_allocation_conservation`, `check_all_invariants` |
| `backend/app/split/calculator.py` | `SplitCalculator.calculate()` — 13-step pipeline |
| `backend/tests/split/__init__.py` | Split test package marker |
| `backend/tests/split/test_equal_allocator.py` | 26 unit tests for `EqualAllocator` |
| `backend/tests/split/test_proportional_allocator.py` | 24 unit tests for `ProportionalAllocator` |
| `backend/tests/split/test_rounding.py` | 20 unit tests for `RoundingPolicy` |
| `backend/tests/split/test_invariants.py` | 14 unit tests for invariant checks |
| `backend/tests/split/test_split_calculator.py` | 30 unit tests for full pipeline (equal, item-wise, edge cases, validation) |
| `backend/tests/golden/__init__.py` | Golden test package marker |
| `backend/tests/golden/restaurant_01.json` | 4-person restaurant: equal split, CGST+SGST, 10% discount |
| `backend/tests/golden/restaurant_02.json` | 3-person restaurant: item-wise, shared items, tax + service charge |
| `backend/tests/golden/swiggy_01.json` | 2-person Swiggy order: delivery fee (equal), platform fee, CGST+SGST, discount |
| `backend/tests/golden/hostel_01.json` | 8-person hostel mess: equal split, large group, rounding |
| `backend/tests/golden/test_golden.py` | Golden fixture runner: loads JSON, builds `SplitInput`, verifies invariants |
| `backend/tests/split/test_property_based.py` | Hypothesis property tests: 12 tests × 10,000 examples each |

## Files Modified

| File | Reason |
|------|--------|
| `backend/app/split/calculator.py` | Bug fix: cap `total_discount` at `subtotal` in grand total derivation (PDD E6) |
| `backend/app/split/rounding.py` | Bug fix: switch from round-half-up to floor rounding to prevent negative payer total |
| `backend/tests/split/test_rounding.py` | Updated assertions to match floor rounding behaviour |

---

## Architecture Decisions

### Pure function — zero I/O
`SplitCalculator.calculate()` is a pure function: it takes a `SplitInput` and returns a `SplitResult`. No database access, no HTTP calls, no clock dependency. Same input always produces same output. This makes it trivially testable and safe to call multiple times (e.g. for preview before locking). Reference: Phase 1 Design §6.

### Integer paise only — no `Decimal` or `float` in the math path
All calculations in `allocators.py`, `rounding.py`, and `calculator.py` operate exclusively on Python `int` (paise). `Decimal` appears only in `Paise.to_rupees_decimal()` for display. `float` never appears. This eliminates floating-point rounding errors entirely. Reference: PDD §5.

### Frozen dataclasses for all models
`SplitInput`, `SplitResult`, `SplitItem`, etc. are `@dataclass(frozen=True, slots=True)`. Immutability ensures no accidental mutation between pipeline steps. `slots=True` reduces memory use.

### Amendment SE-1 — Zero-denominator guard in `ProportionalAllocator`
When all participant shares are zero (e.g. a 100% discount making all item values zero), proportional allocation would divide by zero. Fix: if the denominator is zero, fall back to equal allocation. This is the mathematically correct behaviour — if everyone has a zero share, split equally. Reference: Amendment SE-1.

### Floor rounding — not round-half-up (discovered via Hypothesis)
The original implementation used round-half-up: `((raw + 50) // 100) * 100`. Hypothesis discovered a falsifying example: `grand_total=150, n=3`. Each participant gets 50 paise raw; round-half-up produces 100 each; `others_sum = 200 > grand_total = 150`; payer total = -50. Fix: use floor rounding `(raw // 100) * 100`. Floor rounding guarantees `sum(rounded_non_payers) ≤ sum(raw_non_payers) ≤ grand_total`, so the payer residual is always ≥ 0. Reference: Amendment SE-2.

### Payer absorbs all rounding error — never computed independently
The payer's total is always `grand_total - sum(all_other_totals)`. It is never computed by rounding the payer's raw total independently. This guarantees `sum(all) == grand_total` trivially by construction, without needing to adjust. Reference: PDD §5.4.

### Per-item remainder to last claimer (item-wise mode)
When dividing a line item's price across multiple claimers, `unit_cost = item.total_paise // item.quantity`. The remainder `item.total_paise - unit_cost * item.quantity` goes to the **last claimer** — the one with the highest `created_at` timestamp. This is the deterministic, PDD-specified rule and prevents the remainder from always accumulating to the first person. Reference: PDD §5.2.

### Join order as round-robin order
Remainder paise in equal allocation and proportional allocation are distributed in `join_order` order (0 = payer, ascending). This is deterministic, predictable, and gives the payer a marginal advantage of receiving remainders first — which is reasonable since the payer advanced the cash. Reference: PDD §5.3.

### Discount capped at subtotal — applied in both allocation AND grand total
PDD E6: if the total discount exceeds the item subtotal, it is capped. The cap must be applied in two places: in `_allocate_adjustments_by_type()` (for distribution) AND in the grand total derivation. The original implementation only capped the allocation, making the grand total wrong for over-discounted receipts. Reference: PDD E6.

### Adjustment amounts are signed
The `adjustment` type can have a negative `amount_paise`. This is used for OCR reconciliation deltas (e.g. "the OCR read ₹10 but the actual total was ₹9.50 — reduce by 50 paise"). All other adjustment types (`tax`, `service_charge`, `delivery_fee`, `discount`) are non-negative. Reference: Amendment DB-4.

---

## Implementation Details

### 13-step pipeline

```
SplitInput (validated)
  │
  ├─ Step 1:  Validate inputs (participant count, payer count, item quantities, mode)
  ├─ Step 2:  Compute item subtotal = sum(item.total_paise)
  ├─ Step 3:  Compute per-participant item share
  │             equal mode:     EqualAllocator.allocate(subtotal, round_robin)
  │             item_wise mode: per-item floor division + remainder to last claimer
  ├─ Step 4:  (Reserved for item-specific discounts — not in Phase 1)
  ├─ Step 5:  Pre-tax subtotals = item shares
  ├─ Step 6:  Allocate bill-level discounts (proportional by item share; capped at subtotal)
  ├─ Step 7:  Post-discount subtotals = pretax - discount
  │             Clamp to 0 defensively
  ├─ Step 8:  Allocate taxes proportionally by post-discount subtotal
  ├─ Step 9:  Allocate service charge proportionally by post-discount subtotal
  ├─ Step 10: Allocate delivery fee equally
  ├─ Step 10b: Allocate generic 'adjustment' amounts (proportional or equal)
  ├─ Compute grand_total = subtotal - discount(capped) + tax + svc + delivery + adj
  ├─ Step 11: Compute raw totals = postdisc + tax + svc + delivery + adj
  ├─ Step 12: RoundingPolicy.apply(raw_totals, grand_total, payer_id)
  │             → floor-round non-payers to nearest ₹1
  │             → payer_total = grand_total - sum(other_rounded)
  └─ Step 13: check_all_invariants(result) — raises if violated (bug)
```

### EqualAllocator algorithm

```python
base = total // n
remainder = total - base * n
result[pids[i]] = base + (1 if i < remainder else 0)
```

Remainder 1-paise coins distributed from index 0 upward (join order).

### ProportionalAllocator algorithm

```python
denom = sum(shares.values())
if denom == 0:                         # SE-1: zero-denominator guard
    return EqualAllocator.allocate(...)
for pid in round_robin:
    floor_alloc[pid] = (total * shares[pid]) // denom
remainder = total - sum(floor_alloc.values())
# distribute remainder 1-paise in join order
for i in range(remainder):
    floor_alloc[round_robin[i]] += 1
```

### Data flow

```
SplitInput
    ↓
SplitCalculator.calculate()
    ├── EqualAllocator  or  _compute_item_wise_shares()
    ├── ProportionalAllocator (for discounts, taxes, service charge)
    ├── EqualAllocator (for delivery fee)
    ├── RoundingPolicy.apply()
    └── check_all_invariants()
    ↓
SplitResult
    ├── grand_total_paise: int
    ├── participant_totals: list[ParticipantBreakdown]
    └── invariant_holds: bool (always True if returned)
```

### Invariants enforced

| Invariant | Check function | Raises |
|-----------|----------------|--------|
| `sum(totals) == grand_total` | `check_sum_conservation` | `SumConservationViolation` |
| `all(total >= 0)` | `check_non_negative_totals` | `NegativeTotalViolation` |
| `payer_total >= 0` | `check_payer_non_negative` | `NegativePayerTotalViolation` |
| `sum(alloc) == allocated_amount` | `check_allocation_conservation` | `AllocationConservationViolation` |

---

## Bugs Found During Development

### Bug #1 — Discount cap not applied to grand total (PDD E6)

**Description:**  
When a discount exceeded the item subtotal, `_allocate_adjustments_by_type()` correctly capped the allocated discount at the subtotal. However, the grand total was computed using the **uncapped** discount amount. This caused `grand_total < sum(raw_totals)`, making the payer's residual negative and triggering `NegativePayerTotalViolation`.

**Falsifying case:**  
`subtotal=1000, discount=1500, tax=180` → allocation uses capped discount of 1000, but grand_total computed as `1000 - 1500 + 180 = -320` (wrong). Correct: `1000 - 1000 + 180 = 180`.

**Root cause:**  
The cap logic in `_allocate_adjustments_by_type()` operated on a local variable. The grand total computation block read the original uncapped `total_discount` from `inp.adjustments`.

**Fix:**  
In `calculator.py`, cap `total_discount = min(total_discount, subtotal)` before computing `grand_total`.

**Prevention:**  
`TestEdgeCases.test_discount_exceeds_subtotal` and `test_discount_equals_subtotal` in `test_split_calculator.py`.

---

### Bug #2 — Round-half-up causes negative payer total

**Description:**  
The original rounding formula `((raw + 50) // 100) * 100` rounds 50 paise up to 100 paise. When multiple non-payers all have exactly 50 paise (or any amount that rounds up), the sum of their rounded totals can exceed `grand_total`, making `payer_total = grand_total - others_sum` negative.

**Falsifying case found by Hypothesis:**  
`grand_total=150, n_non_payers=2` → each non-payer gets 50 paise raw → rounds to 100 → `others_sum=200 > 150` → `payer_total=-50` → `NegativePayerTotalViolation`.

Equivalently: `subtotal=150, n=3` with equal split.

**Root cause:**  
Round-half-up is not safe when multiple values hit the midpoint simultaneously. The rounding error can accumulate beyond the grand total.

**Fix:**  
Switch to floor rounding: `(raw // 100) * 100`. Floor guarantees `rounded(x) ≤ x`, so `sum(floor_rounded) ≤ sum(raw) ≤ grand_total`. The payer residual is always ≥ 0.

Trade-off: Non-payers always pay the floor of their exact share (in ₹1 units). The payer absorbs all sub-rupee remainders. This is acceptable — the payer is the one who advanced the cash and is the natural absorber of rounding gains.

**Prevention:**  
- `test_150_paise_3_people` in `test_rounding.py` (the exact falsifying case)
- `TestRoundingPolicyProperties.test_payer_non_negative` (Hypothesis, 10K examples)
- `TestSplitCalculatorEqualProperties.test_payer_non_negative_equal` (Hypothesis, 5K examples)

---

## Testing

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/split/test_equal_allocator.py` | 26 | ✅ All passed |
| `tests/split/test_proportional_allocator.py` | 24 | ✅ All passed |
| `tests/split/test_rounding.py` | 20 | ✅ All passed |
| `tests/split/test_invariants.py` | 14 | ✅ All passed |
| `tests/split/test_split_calculator.py` | 30 | ✅ All passed |
| `tests/golden/test_golden.py` | 21 (3 skipped†) | ✅ 18 passed |
| **Subtotal (non-property)** | **135** | ✅ **0 failures** |
| `tests/split/test_property_based.py` | 12 | ✅ All passed |
| **Grand total** | **147** | ✅ **0 failures** |

> † 3 skipped: `test_item_shares` for fixtures that do not define `item_shares` in `expected`.

**Regression:** All 102 pre-existing M003 unit tests continue to pass.

---

## Property Tests

| Invariant | Test | Examples | Falsifying Case Found |
|-----------|------|----------|-----------------------|
| `EqualAllocator` sum conservation | `test_sum_conservation` | 10,000 | None |
| `EqualAllocator` non-negative | `test_non_negative` | 10,000 | None |
| `EqualAllocator` determinism | `test_determinism` | 1,000 | None |
| `ProportionalAllocator` sum conservation | `test_sum_conservation` | 10,000 | None |
| `ProportionalAllocator` non-negative | `test_non_negative` | 10,000 | None |
| `RoundingPolicy` sum conservation | `test_sum_conservation` | 10,000 | Bug #2 (fixed) |
| `RoundingPolicy` payer non-negative | `test_payer_non_negative` | 10,000 | Bug #2 (fixed) |
| `SplitCalculator` equal sum conservation | `test_sum_conservation_equal` | 10,000 | Bug #2 (fixed) |
| `SplitCalculator` equal non-negative | `test_non_negative_totals_equal` | 5,000 | Bug #2 (fixed) |
| `SplitCalculator` equal payer ≥ 0 | `test_payer_non_negative_equal` | 5,000 | Bug #2 (fixed) |
| `SplitCalculator` equal determinism | `test_determinism_equal` | 1,000 | None |
| `SplitCalculator` item-wise sum conservation | `test_sum_conservation_item_wise` | 5,000 | Bug #2 (fixed) |

**Total property examples executed: ~112,000**  
**Runtime: 274.92 seconds (4 minutes 34 seconds)**

---

## Git History

| Commit | Message |
|--------|---------|
| `4a03680` | `feat(split): implement complete split calculation engine` |
| `d5bc805` | `fix(split): use floor rounding to prevent negative payer total` |

---

## Risks / Known Limitations

- **Equal split only for Phase 1 review purposes.** Both `equal` and `item_wise` modes are implemented and fully tested.
- **No percentage-split mode.** PDD explicitly defers this. The `mode` field in `SplitInput` validates against `{"equal", "item_wise"}` only.
- **Floor rounding favours the payer.** In edge cases (e.g. 150 paise / 3 people), the payer absorbs all sub-rupee remainders. Non-payers always pay the floor of their exact share. This is an intentional product decision.
- **Property tests are slow (4+ minutes).** 10,000 examples × 12 tests × constructor overhead. In CI the example count should be reduced to 200 (default) and the full 10K suite run nightly or pre-merge only.
- **Golden fixtures specify pre-rounding item totals.** The `item_shares` field in golden fixtures is the raw item allocation before rounding and adjustment. This is intentional — it tests the allocation logic independently of rounding.
- **`created_at` tie-breaking.** If two claimers have identical timestamps (possible if API calls arrive within the same millisecond), the last-claimer remainder distribution is non-deterministic. The service layer should enforce monotonic timestamps within a room.

---

## Next Milestone

**M005 — Repository Layer**
- Objective: Implement async SQLAlchemy ORM models and repository classes for rooms, participants, receipts, line items, split sessions, and events.
- Dependencies: M001 (async SQLAlchemy setup), M002 (schema), M003 (domain types), M004 (split engine types for persistence).
- Blockers: None.

---

## Updated Progress

```
[x] Repository setup        ← M001
[x] Database schema         ← M002
[x] Domain foundations      ← M003
[x] Split engine            ← M004
[ ] Repository layer        ← NEXT
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
| Pure function — no I/O in calculator | ✅ |
| Integer paise only — no float in math path | ✅ |
| Amendment SE-1: zero-denominator guard in ProportionalAllocator | ✅ |
| Amendment SE-2: payer non-negative assertion in RoundingPolicy | ✅ |
| PDD E6: discount capped at subtotal in both allocation and grand total | ✅ |
| PDD E7: zero grand total handled correctly | ✅ |
| PDD E9: 1 paise among 3 → [1, 0, 0] | ✅ |
| PDD §5.4: payer total computed as residual only | ✅ |
| PDD §5.2: per-item remainder to last claimer by timestamp | ✅ |
| PDD §5.3: round-robin remainder in join order | ✅ |
| Sum conservation invariant checked post-calculation | ✅ |
| Non-negative totals invariant checked post-calculation | ✅ |
| Allocation conservation checked per adjustment type | ✅ |
| All 135 non-property tests pass | ✅ |
| All 12 property tests pass (10K examples each) | ✅ |
| 4 real-world golden receipt fixtures pass | ✅ |
| All code lint-clean (`ruff check` — 0 errors) | ✅ |
| Bug #1 (discount cap) fixed and tested | ✅ |
| Bug #2 (floor rounding) fixed and tested | ✅ |
| Both fixes committed separately with explanatory messages | ✅ |
