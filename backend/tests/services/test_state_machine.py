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

def test_invalid_transitions():
    assert can_transition("draft", "settling") is False
    assert can_transition("active", "draft") is False
    assert can_transition("settling", "archived") is False

    with pytest.raises(InvalidStateTransition):
        validate_transition("draft", "settling")

def test_archived_is_terminal():
    assert can_transition("archived", "active") is False
    assert can_transition("archived", "draft") is False
    assert can_transition("archived", "settling") is False

    with pytest.raises(InvalidStateTransition):
        validate_transition("archived", "active")
