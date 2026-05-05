from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal

router = APIRouter(tags=["health"])

_REQUIRED_TABLES = ("alembic_version", "users", "audit_logs")


def _check_database() -> str:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"


def _check_required_tables() -> dict[str, str]:
    checks: dict[str, str] = {}
    try:
        with SessionLocal() as session:
            for table_name in _REQUIRED_TABLES:
                try:
                    session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                    checks[table_name] = "ok"
                except Exception:
                    checks[table_name] = "unavailable"
    except Exception:
        return {table_name: "unavailable" for table_name in _REQUIRED_TABLES}
    return checks


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
    """Strict readiness probe - fails fast when database or core schema is down."""
    settings = get_settings()
    database_status = _check_database()
    table_checks = _check_required_tables() if database_status == "ok" else {}
    schema_status = "ok" if table_checks and all(value == "ok" for value in table_checks.values()) else "unavailable"
    body: dict[str, object] = {
        "status": "ready" if database_status == "ok" and schema_status == "ok" else "not_ready",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "database": {"status": database_status},
        "schema": {"status": schema_status, "required_tables": table_checks},
    }
    if body["status"] != "ready":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=body)
    return body
