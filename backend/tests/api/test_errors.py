import pytest

from app.api.errors import domain_error_status
from app.shared.errors import (
    DomainError,
    InvalidStateTransition,
    InvalidToken,
    NotAuthorized,
    RoomAlreadyLocked,
    RoomFull,
    RoomNotFound,
    VersionConflict,
)

pytestmark = pytest.mark.asyncio


async def test_domain_error_to_http_mapping() -> None:
    assert domain_error_status(InvalidStateTransition("draft", "settling")) == 400
    assert domain_error_status(NotAuthorized()) == 403
    assert domain_error_status(InvalidToken()) == 403
    assert domain_error_status(RoomNotFound()) == 404
    assert domain_error_status(RoomFull()) == 409
    assert domain_error_status(VersionConflict()) == 409
    assert domain_error_status(RoomAlreadyLocked()) == 409
    assert domain_error_status(DomainError("UNMAPPED", "Unknown")) == 500
