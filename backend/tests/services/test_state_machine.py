import pytest

from app.domain.room_state_machine import (
    can_transition,
    validate_transition,
)
from app.shared.errors import InvalidStateTransition


def test_valid_transitions():
    assert can_transition("draft", "active") is True
    assert can_transition("draft", "archived") is True
    assert can_transition("active", "settling") is True
    assert can_transition("active", "archived") is True
    assert can_transition("settling", "active") is True
    assert can_transition("settling", "settled") is True
    assert can_transition("settled", "archived") is True

def test_invalid_transitions():
    assert can_transition("draft", "settling") is False
    assert can_transition("draft", "settled") is False
    assert can_transition("active", "draft") is False
    assert can_transition("settling", "archived") is False

    with pytest.raises(InvalidStateTransition):
        validate_transition("draft", "settling")
    with pytest.raises(InvalidStateTransition):
        validate_transition("draft", "settled")

def test_terminal_states():
    # archived is terminal
    assert can_transition("archived", "active") is False
    assert can_transition("archived", "draft") is False
    assert can_transition("archived", "settling") is False

    # expired is terminal
    assert can_transition("expired", "active") is False
    assert can_transition("expired", "draft") is False
    assert can_transition("expired", "settling") is False

    with pytest.raises(InvalidStateTransition):
        validate_transition("archived", "active")
    with pytest.raises(InvalidStateTransition):
        validate_transition("expired", "active")
