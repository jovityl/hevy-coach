from fastapi import FastAPI

from app.api.routers import auth, health, ingest, metrics
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(metrics.router)
