from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi.responses import JSONResponse

from app.api.schemas.common import ErrorResponse
from app.shared.errors import DomainError

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad request"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Semantic validation failed"},
    423: {"model": ErrorResponse, "description": "Locked"},
    500: {"model": ErrorResponse, "description": "Internal error"},
}


def domain_error_status(exc: DomainError) -> int:
    status_map: dict[str, int] = {
        "INVALID_VPA_FORMAT": 400,
        "INVALID_CLAIM_QUANTITY": 400,
        "INVALID_ITEM_NAME": 400,
        "INVALID_NICKNAME": 400,
        "INVALID_COLOR": 400,
        "AMOUNT_TOO_LARGE": 400,
        "MAX_ITEMS_EXCEEDED": 400,
        "MAX_ADJUSTMENTS_EXCEEDED": 400,
        "ITEM_QUANTITY_ZERO": 400,
        "QUANTITY_BELOW_CLAIMED": 400,
        "NO_ITEMS": 400,
        "INVALID_ADJUSTMENT_AMOUNT": 400,
        "INVALID_STATE_TRANSITION": 400,
        "CLAIM_NOT_FOUND": 404,
        "ROOM_NOT_FOUND": 404,
        "ITEM_NOT_FOUND": 404,
        "SPLIT_SESSION_NOT_FOUND": 404,
        "NOT_AUTHORIZED": 403,
        "INVALID_TOKEN": 403,
        "ROOM_FULL": 409,
        "ROOM_ALREADY_LOCKED": 409,
        "ITEM_ALREADY_CLAIMED": 409,
        "VERSION_CONFLICT": 409,
        "ITEM_HAS_CLAIMS": 409,
        "WRONG_SPLIT_MODE": 409,
        "UNCLAIMED_ITEMS_EXIST": 400,
        "VPA_NOT_SET": 422,
        "INSUFFICIENT_PARTICIPANTS": 422,
        "ROOM_LOCKED": 423,
        "RECEIPT_LOCKED": 423,
        "ROOM_EXPIRED": 403,
        "ROOM_CLOSED": 403,
        "SPLIT_INVARIANT_FAILED": 500,
        "INTERNAL_ERROR": 500,
    }
    return status_map.get(exc.code, 500)


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, DomainError):
        raise exc
    status_code = domain_error_status(exc)
    logger.info("Domain error [%s] on %s %s", exc.code, request.method, request.url.path)
    return JSONResponse(status_code=status_code, content={"error": exc.to_dict()})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
