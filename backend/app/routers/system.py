from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.dependencies import CurrentUser, DbSession
from app.schemas.reports import PublicSystemInfoResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info", response_model=PublicSystemInfoResponse)
def get_public_system_info(db: DbSession, current_user: CurrentUser) -> PublicSystemInfoResponse:
    settings = get_settings()
    database_status = "unavailable"
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "unavailable"
    return PublicSystemInfoResponse(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        dhis2_base_url=settings.dhis2_base_url,
        ai_provider=settings.ai_provider or None,
        ai_model=settings.ai_model or None,
        database_status=database_status,
    )
