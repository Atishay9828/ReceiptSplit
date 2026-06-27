from __future__ import annotations

from app.shared.errors import InvalidToken, NotAuthorized


class InvalidJwt(InvalidToken):
    """JWT is malformed, expired, untrusted, or fails provider validation."""


class UserAuthRequired(NotAuthorized):
    """A user JWT is required; capability tokens are not sufficient."""


class RoomOwnerRequired(NotAuthorized):
    """The authenticated user does not own the room."""
