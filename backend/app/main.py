"""
ReceiptSplit FastAPI application factory.

The app owns framework concerns only: middleware, exception registration,
router registration, and process-level settings.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.config import settings
from app.security.rate_limit import limiter

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    limiter.reset()
    application = FastAPI(
        title="ReceiptSplit API",
        description="UPI-native, receipt-first bill splitting for India.",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "If-None-Match"],
        max_age=600,
    )

    register_exception_handlers(application)

    creation_counts: dict[str, tuple[int, datetime]] = defaultdict(
        lambda: (0, datetime.now(tz=UTC))
    )

    @application.middleware("http")
    async def room_creation_rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "POST" and request.url.path == "/api/rooms":
            ip = request.client.host if request.client else "unknown"
            count, window_start = creation_counts[ip]
            now = datetime.now(tz=UTC)
            if now - window_start > timedelta(hours=1):
                creation_counts[ip] = (1, now)
            elif count >= settings.room_creation_rate_limit_per_hour:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Too many rooms created. Try again later.",
                        }
                    },
                )
            else:
                creation_counts[ip] = (count + 1, window_start)
        return await call_next(request)

    if settings.is_development:

        @application.middleware("http")
        async def timing_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
            start = time.perf_counter()
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                "%s %s -> %d (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            return response

    application.include_router(api_router)
    logger.info("ReceiptSplit API started (env=%s)", settings.env)
    return application


app: FastAPI = create_app()
