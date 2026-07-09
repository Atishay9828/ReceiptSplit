"""
ReceiptSplit - Split Calculator

Implements the deterministic 13-step calculation pipeline from PDD section 5.1.

This is a pure function: no DB access, no I/O, no side effects.
Same input always produces same output. No randomness, no clock dependency.

Pipeline steps:
  1.  Validate inputs
  2.  Compute item subtotal
  3.  Compute per-participant item share (mode-dependent)
  4.  (Reserved for item-specific discounts — not in Phase 1)
  5.  Pre-tax subtotals
  6.  Allocate bill-level discounts
  7.  Post-discount subtotals
  8.  Allocate taxes proportionally
  9.  Allocate service charge proportionally
  10. Allocate delivery fee equally
  11. Compute raw totals (including generic adjustments)
  12. Apply rounding
  13. Assert invariants

Design authority:
  - PDD section 5.1 (13-step pipeline)
  - PDD section 5.2 (per-mode item share)
  - PDD section 5.3 (round-robin order)
  - PDD section 5.4 (payer = residual)
  - Phase 1 Implementation Design section 6
  - Amendment SE-1 (zero-denominator guard)
  - Amendment SE-2 (payer non-negative assertion)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from app.split.allocators import EqualAllocator, ProportionalAllocator
from app.split.invariants import check_all_invariants, check_allocation_conservation
from app.split.models import ParticipantBreakdown, SplitResult
from app.split.rounding import RoundingPolicy

if TYPE_CHECKING:
    from uuid import UUID

if True:
    from app.split.models import SplitInput


class SplitCalculator:
    """Deterministic split calculation engine.

    Usage:
        result = SplitCalculator.calculate(split_input)
    """

    @staticmethod
    def calculate(inp: SplitInput) -> SplitResult:
        """Execute the 13-step split calculation pipeline.

        Args:
            inp: Complete, validated SplitInput.

        Returns:
            SplitResult with per-participant breakdowns and grand total.

        Raises:
            SplitInvariantFailed: if any invariant check fails (bug).
            ValueError: if input validation fails (caller bug).
        """
        # ── Step 1: Validate inputs ──────────────────────────────────────
        _validate_input(inp)

        # Extract participant IDs in join order (the canonical round-robin).
        round_robin = [p.id for p in inp.participants]
        payer_id = _find_payer_id(inp)

        # ── Step 2: Compute item subtotal ────────────────────────────────
        subtotal = sum(item.total_paise for item in inp.items)

        # ── Step 3: Compute per-participant item share ───────────────────
        if inp.mode == "equal":
            items_share = _compute_equal_shares(subtotal, round_robin)
        elif inp.mode == "item_wise":
            items_share = _compute_item_wise_shares(inp, round_robin)
        else:
            msg = f"Unsupported split mode: {inp.mode!r}"
            raise ValueError(msg)

        # ── Step 4: Item-specific discounts (reserved, not in Phase 1) ───
        # No-op. Item total_paise already reflects any pre-calculation discounts.

        # ── Step 5: Pre-tax subtotals ────────────────────────────────────
        pretax: dict[UUID, int] = dict(items_share)

        # ── Step 6: Allocate bill-level discounts ────────────────────────
        discount_alloc = _allocate_adjustments_by_type(
            "discount", inp.adjustments, pretax, round_robin, subtotal, amount_base_paise=subtotal
        )

        # ── Step 7: Post-discount subtotals ──────────────────────────────
        postdisc: dict[UUID, int] = {}
        for pid in round_robin:
            postdisc[pid] = pretax[pid] - discount_alloc.get(pid, 0)

        # PDD E6: Discount > subtotal -> cap at subtotal. Post-discount = 0.
        # After proportional allocation, individual post-discount values should
        # not go negative. But we clamp defensively.
        for pid in round_robin:
            if postdisc[pid] < 0:
                postdisc[pid] = 0

        postdisc_subtotal = sum(postdisc.values())

        # ── Step 8: Allocate taxes proportionally ────────────────────────
        tax_alloc = _allocate_adjustments_by_type(
            "tax", inp.adjustments, postdisc, round_robin, postdisc_subtotal, amount_base_paise=subtotal
        )

        # ── Step 9: Allocate service charge proportionally ───────────────
        svc_alloc = _allocate_adjustments_by_type(
            "service_charge",
            inp.adjustments,
            postdisc,
            round_robin,
            postdisc_subtotal,
            amount_base_paise=subtotal,
        )

        # ── Step 10: Allocate delivery fee equally ───────────────────────
        delivery_alloc = _allocate_adjustments_by_type(
            "delivery_fee",
            inp.adjustments,
            postdisc,
            round_robin,
            postdisc_subtotal,
            amount_base_paise=subtotal,
        )

        # ── Step 10b: Allocate generic adjustments ───────────────────────
        # 'adjustment' type (OCR reconciliation, etc.) — uses its own allocation method.
        adjustment_alloc = _allocate_adjustments_by_type(
            "adjustment",
            inp.adjustments,
            postdisc,
            round_robin,
            postdisc_subtotal,
            amount_base_paise=subtotal,
        )

        # ── Compute grand total ──────────────────────────────────────────
        # PDD §5.5: grand_total = subtotal + sum(taxes) + service_charge
        #           + delivery_fee - sum(discounts) + sum(adjustments)
        total_discount = sum(
            _adjustment_effect_amount(a, subtotal) for a in inp.adjustments if a.type == "discount"
        )
        # PDD E6: Discount > subtotal → cap at subtotal.
        # This cap must be applied to grand_total too, not just the allocation.
        if total_discount > subtotal:
            total_discount = subtotal

        total_tax = sum(
            _adjustment_effect_amount(a, subtotal) for a in inp.adjustments if a.type == "tax"
        )
        total_svc = sum(
            _adjustment_effect_amount(a, subtotal)
            for a in inp.adjustments
            if a.type == "service_charge"
        )
        total_delivery = sum(
            _adjustment_effect_amount(a, subtotal)
            for a in inp.adjustments
            if a.type == "delivery_fee"
        )
        total_adjustment = sum(
            _adjustment_effect_amount(a, subtotal)
            for a in inp.adjustments
            if a.type == "adjustment"
        )

        grand_total = (
            subtotal - total_discount + total_tax + total_svc + total_delivery + total_adjustment
        )

        # ── Step 11: Compute raw totals ──────────────────────────────────
        raw_totals: dict[UUID, int] = {}
        for pid in round_robin:
            raw_totals[pid] = (
                postdisc[pid]
                + tax_alloc.get(pid, 0)
                + svc_alloc.get(pid, 0)
                + delivery_alloc.get(pid, 0)
                + adjustment_alloc.get(pid, 0)
            )

        # ── Step 12: Apply rounding ──────────────────────────────────────
        # Payer's total is derived as residual (PDD §5.4).
        rounded = RoundingPolicy.apply(raw_totals, grand_total, payer_id)

        # ── Build result ─────────────────────────────────────────────────
        totals: list[ParticipantBreakdown] = []
        for p in inp.participants:
            totals.append(
                ParticipantBreakdown(
                    participant_id=p.id,
                    items_paise=items_share.get(p.id, 0),
                    discount_paise=discount_alloc.get(p.id, 0),
                    tax_paise=tax_alloc.get(p.id, 0),
                    service_charge_paise=svc_alloc.get(p.id, 0),
                    delivery_fee_paise=delivery_alloc.get(p.id, 0),
                    adjustment_paise=adjustment_alloc.get(p.id, 0),
                    total_paise=rounded[p.id],
                    is_payer=p.is_payer,
                )
            )

        result = SplitResult(
            grand_total_paise=grand_total,
            participant_totals=totals,
            invariant_holds=True,
        )

        # ── Step 13: Assert invariants ───────────────────────────────────
        check_all_invariants(result)

        return result


# ── Private helpers ──────────────────────────────────────────────────────────


def _validate_input(inp: SplitInput) -> None:
    """Step 1: Validate the SplitInput.

    Raises ValueError on invalid input (caller bug, not user error).
    """
    if len(inp.participants) < 2:
        msg = f"Split requires >= 2 participants, got {len(inp.participants)}"
        raise ValueError(msg)

    payer_count = sum(1 for p in inp.participants if p.is_payer)
    if payer_count != 1:
        msg = f"Exactly one payer required, got {payer_count}"
        raise ValueError(msg)

    for item in inp.items:
        if item.quantity < 1:
            msg = f"Item {item.id} has quantity {item.quantity} (must be >= 1)"
            raise ValueError(msg)
        if item.total_paise < 0:
            msg = f"Item {item.id} has negative total_paise {item.total_paise}"
            raise ValueError(msg)

    if inp.mode not in ("equal", "item_wise"):
        msg = f"Invalid split mode: {inp.mode!r}"
        raise ValueError(msg)

    if inp.mode == "item_wise":
        _validate_item_wise_assignments(inp)


def _validate_item_wise_assignments(inp: SplitInput) -> None:
    """Verify all items are fully assigned in item_wise mode.

    PDD §5.2: "Precondition to lock: All items must be fully claimed."
    """
    from app.shared.errors import UnclaimedItemsExist

    # Build a map of item_id -> total assigned qty
    assigned: dict[UUID, int] = defaultdict(int)
    for a in inp.assignments:
        assigned[a.item_id] += a.claimed_qty

    unclaimed_ids = []
    for item in inp.items:
        total_assigned = assigned.get(item.id, 0)
        if total_assigned != item.quantity:
            unclaimed_ids.append(str(item.id))

    if unclaimed_ids:
        raise UnclaimedItemsExist(unclaimed_ids)


def _find_payer_id(inp: SplitInput) -> UUID:
    """Extract the payer's UUID."""
    for p in inp.participants:
        if p.is_payer:
            return p.id
    # Should never reach here — _validate_input checks for exactly one payer.
    msg = "No payer found (validation should have caught this)"
    raise ValueError(msg)


def _compute_equal_shares(
    subtotal: int,
    round_robin: list[UUID],
) -> dict[UUID, int]:
    """PDD §5.2 Equal Split: floor(subtotal / N), remainder round-robin."""
    return EqualAllocator.allocate(subtotal, round_robin)


def _compute_item_wise_shares(
    inp: SplitInput,
    round_robin: list[UUID],
) -> dict[UUID, int]:
    """PDD §5.2 Item-Wise Split.

    For each item:
      unit_cost = floor(item.total_paise / item.quantity)
      per assignment: cost = unit_cost * claimed_qty
      item remainder = item.total_paise - (unit_cost * item.quantity)
      remainder goes to the last claimer (by created_at timestamp).

    Every participant gets a result, even if they claimed nothing (= 0).
    """
    shares: dict[UUID, int] = dict.fromkeys(round_robin, 0)

    # Group assignments by item for remainder distribution.
    item_assignments: dict[UUID, list[tuple[UUID, int, float]]] = defaultdict(list)
    for a in inp.assignments:
        # Use timestamp as float for sorting (deterministic tie-breaking).
        item_assignments[a.item_id].append(
            (a.participant_id, a.claimed_qty, a.created_at.timestamp())
        )

    for item in inp.items:
        unit_cost = item.total_paise // item.quantity
        item_remainder = item.total_paise - (unit_cost * item.quantity)

        assignments = item_assignments.get(item.id, [])

        for pid, claimed_qty, _ in assignments:
            shares[pid] += unit_cost * claimed_qty

        # Per-item remainder: added to the last claimer (by created_at).
        # PDD §5.2: "Per-item integer-division remainder: Added to the
        # last claimer of that item (by claim timestamp)."
        if item_remainder > 0 and assignments:
            # Sort by created_at ascending — last claimer is the one with
            # the latest timestamp.
            sorted_claims = sorted(assignments, key=lambda x: x[2])
            last_claimer_id = sorted_claims[-1][0]
            shares[last_claimer_id] += item_remainder

    return shares


def _allocate_adjustments_by_type(
    adj_type: str,
    adjustments: list,
    shares: dict[UUID, int],
    round_robin: list[UUID],
    shares_subtotal: int,
    amount_base_paise: int | None = None,
) -> dict[UUID, int]:
    """Allocate all adjustments of a given type across participants.

    Each adjustment specifies its own allocation method ('proportional' or 'equal').
    Multiple adjustments of the same type are summed first if they use the same
    allocation method.

    For discounts: the total is capped at the subtotal (PDD E6).

    Returns a dict of participant_id -> total allocated paise for this adj_type.
    """
    # Filter to just this type.
    typed_adjs = [a for a in adjustments if a.type == adj_type]
    if not typed_adjs:
        return dict.fromkeys(round_robin, 0)

    # Sum the total for this adjustment type.
    amount_base = shares_subtotal if amount_base_paise is None else amount_base_paise
    total_amount = sum(_adjustment_effect_amount(a, amount_base) for a in typed_adjs)

    # PDD E6: Discount > subtotal -> cap at subtotal.
    if adj_type == "discount":
        item_subtotal = sum(shares.values())
        if total_amount > item_subtotal:
            total_amount = item_subtotal

    # If total is zero (or negative for non-adjustment types which shouldn't happen),
    # return zeros.
    if total_amount == 0:
        return dict.fromkeys(round_robin, 0)

    # Determine allocation method. If mixed methods exist for the same type,
    # split into proportional and equal portions separately.
    proportional_total = sum(
        _adjustment_effect_amount(a, amount_base)
        for a in typed_adjs
        if a.allocation == "proportional"
    )
    equal_total = sum(
        _adjustment_effect_amount(a, amount_base)
        for a in typed_adjs
        if a.allocation == "equal"
    )

    # Cap proportional and equal totals for discounts.
    if adj_type == "discount":
        item_subtotal = sum(shares.values())
        combined = proportional_total + equal_total
        if combined > item_subtotal and combined > 0:
            # Scale each down proportionally.
            proportional_total = (proportional_total * item_subtotal) // combined
            equal_total = item_subtotal - proportional_total

    result: dict[UUID, int] = dict.fromkeys(round_robin, 0)

    if proportional_total != 0:
        prop_alloc = ProportionalAllocator.allocate(abs(proportional_total), shares, round_robin)
        check_allocation_conservation(
            prop_alloc, abs(proportional_total), f"{adj_type}(proportional)"
        )
        sign = 1 if proportional_total >= 0 else -1
        for pid in round_robin:
            result[pid] += sign * prop_alloc.get(pid, 0)

    if equal_total != 0:
        eq_alloc = EqualAllocator.allocate(abs(equal_total), round_robin)
        check_allocation_conservation(eq_alloc, abs(equal_total), f"{adj_type}(equal)")
        sign = 1 if equal_total >= 0 else -1
        for pid in round_robin:
            result[pid] += sign * eq_alloc.get(pid, 0)

    return result


def _adjustment_effect_amount(adjustment, base_paise: int) -> int:
    if adjustment.rate_basis_points is None:
        amount = adjustment.amount_paise
    else:
        amount = (max(base_paise, 0) * adjustment.rate_basis_points) // 10_000
    if adjustment.type == "discount":
        return abs(amount)
    if adjustment.type in {"tax", "service_charge", "delivery_fee"}:
        return abs(amount)
    return amount
