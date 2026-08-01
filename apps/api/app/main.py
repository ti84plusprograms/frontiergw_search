from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.airports import router as airports_router
from app.api.errors import (
    routing_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.api.health import router as health_router
from app.api.middleware import request_context_middleware
from app.api.schedules import router as schedules_router
from app.api.search import router as search_router
from app.core.config import settings
from app.domain.errors import RoutingError

app = FastAPI(
    title="Frontier GoWild Destination Explorer API",
    version="0.4.0",
)

# Request ID + security headers (runs for every request).
app.middleware("http")(request_context_middleware)

# CORS: explicit origins only, never a production wildcard (PHASE.md §Security).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# Consistent error envelope for all failures (ADR-009).
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RoutingError, routing_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router, prefix="/api/v1")
app.include_router(airports_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")
