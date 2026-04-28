from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, object]:
    settings = get_settings()
    database_status = "not_checked"

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "unavailable"

    return {
        "status": "ok",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "database": {
            "status": database_status,
            "note": "Foundational connectivity check only; deeper readiness checks come later.",
        },
    }

