"""
ReceiptSplit — Room State Machine

Pure domain logic for room lifecycle transitions.
No database access. No I/O. No side effects.

Valid transitions:
    draft    → active
    draft    → archived
    active   → settling
    active   → archived
    settling → active
    archived → (terminal — no outgoing transitions)

Design authority:
    - PDD §3 (Room Lifecycle)
    - Phase 1 Design Amendments TXN-1
"""

from __future__ import annotations

from app.shared.errors import InvalidStateTransition

# ── Transition table ──────────────────────────────────────────────────────────

# Frozen: {from_state: frozenset(allowed_to_states)}
_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"active", "archived"}),
    "active": frozenset({"settling", "archived"}),
    "settling": frozenset({"active", "settled"}),
    "settled": frozenset({"archived"}),
    "expired": frozenset(),
    "archived": frozenset(),  # terminal — no outgoing transitions
}

# All valid states for guard checks.
VALID_STATES: frozenset[str] = frozenset(_TRANSITIONS.keys())


# ── Public API ────────────────────────────────────────────────────────────────


def can_transition(from_state: str, to_state: str) -> bool:
    """Check whether a transition is allowed (read-only, never raises)."""
    allowed = _TRANSITIONS.get(from_state, frozenset())
    return to_state in allowed


def validate_transition(from_state: str, to_state: str) -> None:
    """
    Validate a state transition.

    Raises:
        InvalidStateTransition: if the transition is not allowed.
    """
    if from_state not in VALID_STATES:
        raise InvalidStateTransition(from_state, to_state)
    if not can_transition(from_state, to_state):
        raise InvalidStateTransition(from_state, to_state)


def allowed_targets(from_state: str) -> frozenset[str]:
    """Return the set of states reachable from `from_state`."""
    return _TRANSITIONS.get(from_state, frozenset())
