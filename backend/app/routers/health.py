from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal

router = APIRouter(tags=["health"])


def _check_database() -> str:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"


@router.get("/health")
def health_check() -> dict[str, object]:
    """Lightweight liveness/status endpoint.

    This stays 200 so operators can inspect the process even when a dependency
    is down. Render uses /ready for strict traffic health.
    """
    settings = get_settings()
    database_status = _check_database()
    return {
        "status": "ok",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "database": {
            "status": database_status,
            "note": "Health endpoint exposes database availability only, not credentials.",
        },
    }


@router.get("/ready")
def readiness_check() -> dict[str, object]:
    """Strict readiness probe - fails fast (503) when the database is down."""
    settings = get_settings()
    database_status = _check_database()
    body: dict[str, object] = {
        "status": "ready" if database_status == "ok" else "not_ready",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "database": {"status": database_status},
    }
    if database_status != "ok":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=body)
    return body
