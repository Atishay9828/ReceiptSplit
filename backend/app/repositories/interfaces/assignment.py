from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.line_item_assignment import LineItemAssignment


class AssignmentRepository(Protocol):
    async def create(self, db: AsyncSession, assignment: LineItemAssignment) -> LineItemAssignment:
        """Persists a new line item assignment."""
        ...

    async def delete_by_participant_and_item(
        self, db: AsyncSession, item_id: UUID, participant_id: UUID
    ) -> bool:
        """Deletes a specific assignment. Returns True if a row was deleted."""
        ...

    async def list_by_room(self, db: AsyncSession, room_id: UUID) -> list[LineItemAssignment]:
        """Lists all assignments for a room."""
        ...

    async def get_claimed_qty(self, db: AsyncSession, item_id: UUID) -> int:
        """Returns the total claimed quantity for an item (SUM of claimed_qty)."""
        ...

    async def delete_by_participant(self, db: AsyncSession, participant_id: UUID) -> None:
        """Deletes all assignments for a given participant."""
        ...
