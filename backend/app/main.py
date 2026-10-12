from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.catalog import router as catalog_router
from backend.app.api.health import router as health_router
from backend.app.api.places import router as places_router
from backend.app.core.config import settings

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(catalog_router)
app.include_router(places_router)
