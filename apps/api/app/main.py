from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from secrets import compare_digest

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.airports import router as airports_router
from app.api.errors import (
    http_exception_handler,
    rate_limit_exception_handler,
    routing_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.api.health import router as health_router
from app.api.middleware import request_context_middleware
from app.api.schedules import router as schedules_router
from app.api.search import router as search_router
from app.core.config import settings
from app.core.metrics import APPLICATION_INFO
from app.core.monitoring import initialize_monitoring
from app.core.observability import configure_logging, log_event
from app.domain.errors import RoutingError
from app.services.rate_limit import RateLimitExceeded


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    configure_logging()
    initialize_monitoring()
    APPLICATION_INFO.labels(environment=settings.app_env, release=settings.app_release).set(1)
    log_event("application.started", environment=settings.app_env, release=settings.app_release)
    yield
    log_event("application.stopped", environment=settings.app_env, release=settings.app_release)


app = FastAPI(
    title="Frontier GoWild Destination Explorer API",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS: explicit origins only, never a production wildcard (PHASE.md §Security).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=[
        "X-Request-ID",
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
    ],
)

# Register after CORS so request IDs/security headers wrap even preflight responses.
app.middleware("http")(request_context_middleware)

# Consistent error envelope for all failures (ADR-009).
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RoutingError, routing_error_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router, prefix="/api/v1")
app.include_router(airports_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    if not settings.metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if settings.metrics_bearer_token:
        expected = f"Bearer {settings.metrics_bearer_token}"
        supplied = request.headers.get("authorization", "")
        if not compare_digest(supplied, expected):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
