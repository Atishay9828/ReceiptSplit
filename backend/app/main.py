"""
ReceiptSplit — FastAPI Application Factory

Creates and configures the FastAPI application instance.
This module is intentionally thin — all logic lives in modules.

Entry point:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.shared.errors import DomainError

# ── Configure logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Application factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    application = FastAPI(
        title="ReceiptSplit API",
        description="UPI-native, receipt-first bill splitting for India.",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    # ── Domain error handler ───────────────────────────────────────────────────
    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        """
        Converts DomainError subclasses to the standard API error response format.
        HTTP status codes are mapped here — the domain layer is HTTP-unaware.
        """
        status_code = _domain_error_to_status(exc)
        logger.info("Domain error [%s] on %s %s", exc.code, request.method, request.url.path)
        return JSONResponse(status_code=status_code, content={"error": exc.to_dict()})

    # ── In-process room creation rate limiter (Amendment API-3) ───────────────
    # NOT a replacement for Phase 5 rate limiting.  Lightweight IP guard only.
    _creation_counts: dict[str, tuple[int, datetime]] = defaultdict(
        lambda: (0, datetime.now(tz=timezone.utc))
    )

    @application.middleware("http")
    async def room_creation_rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "POST" and request.url.path == "/api/rooms":
            ip = request.client.host if request.client else "unknown"
            count, window_start = _creation_counts[ip]
            now = datetime.now(tz=timezone.utc)
            if now - window_start > timedelta(hours=1):
                _creation_counts[ip] = (1, now)
            elif count >= settings.room_creation_rate_limit_per_hour:
                return JSONResponse(
                    status_code=429,
                    content={"error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many rooms created. Try again later.",
                    }},
                )
            else:
                _creation_counts[ip] = (count + 1, window_start)
        return await call_next(request)

    # ── Request timing (development) ──────────────────────────────────────────
    if settings.is_development:
        @application.middleware("http")
        async def timing_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
            start = time.perf_counter()
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug("%s %s → %d (%.1fms)", request.method, request.url.path, response.status_code, elapsed_ms)
            return response

    # ── Health check ──────────────────────────────────────────────────────────
    @application.get("/health", tags=["ops"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    # ── Route registration (add as modules are built) ─────────────────────────
    # from app.rooms.router import router as rooms_router
    # application.include_router(rooms_router, prefix="/api")
    # from app.participants.router import router as participants_router
    # application.include_router(participants_router, prefix="/api")

    logger.info("ReceiptSplit API started (env=%s)", settings.env)
    return application


def _domain_error_to_status(exc: DomainError) -> int:
    """
    Maps DomainError codes to HTTP status codes.
    Matches the error catalog in PDD §16.2.
    """
    status_map: dict[str, int] = {
        # 400 Bad Request
        "INVALID_VPA_FORMAT": 400,
        "INVALID_CLAIM_QUANTITY": 400,
        "INVALID_ITEM_NAME": 400,
        "INVALID_NICKNAME": 400,
        "AMOUNT_TOO_LARGE": 400,
        "MAX_ITEMS_EXCEEDED": 400,
        "MAX_ADJUSTMENTS_EXCEEDED": 400,
        "ITEM_QUANTITY_ZERO": 400,
        "QUANTITY_BELOW_CLAIMED": 400,
        "NO_ITEMS": 400,
        "INVALID_ADJUSTMENT_AMOUNT": 400,
        # 403 Forbidden
        "ROOM_FULL": 403,
        "ROOM_EXPIRED": 403,
        "ROOM_CLOSED": 403,
        "NOT_AUTHORIZED": 403,
        "INVALID_TOKEN": 403,
        # 404 Not Found
        "ROOM_NOT_FOUND": 404,
        "ITEM_NOT_FOUND": 404,
        # 409 Conflict
        "ITEM_ALREADY_CLAIMED": 409,
        "VERSION_CONFLICT": 409,
        "INVALID_STATE_TRANSITION": 409,
        "ITEM_HAS_CLAIMS": 409,
        "WRONG_SPLIT_MODE": 409,
        # 422 Unprocessable
        "UNCLAIMED_ITEMS_EXIST": 422,
        "VPA_NOT_SET": 422,
        "INSUFFICIENT_PARTICIPANTS": 422,
        # 423 Locked
        "ROOM_LOCKED": 423,
        "RECEIPT_LOCKED": 423,
        # 500 Internal
        "SPLIT_INVARIANT_FAILED": 500,
        "INTERNAL_ERROR": 500,
    }
    return status_map.get(exc.code, 500)


# ── Module-level app instance ─────────────────────────────────────────────────
app: FastAPI = create_app()
