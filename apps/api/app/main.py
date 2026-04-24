"""FastAPI application entrypoint for OCR, parsing, and validation workflows."""

from fastapi import FastAPI

from app.api.routes.blockers import router as blockers_router
from app.api.routes.health import router as health_router
from app.core.config import settings

app = FastAPI(
    title="AcadCheck API",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health_router)
app.include_router(blockers_router)


@app.get("/")
def root() -> dict[str, str]:
    """Return a minimal service status payload."""
    return {
        "service": "acadcheck-api",
        "status": "ok",
        "environment": settings.environment,
    }
