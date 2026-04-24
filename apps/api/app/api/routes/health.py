"""Healthcheck route definitions."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """Return a simple health status for uptime probes."""
    return {"status": "ok"}
