from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="Frontier GoWild Destination Explorer API")

app.include_router(health_router, prefix="/api/v1")
