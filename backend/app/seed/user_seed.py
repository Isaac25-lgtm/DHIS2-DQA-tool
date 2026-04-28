from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.base import UserRole
from app.schemas.user import UserCreate
from app.services.user_service import create_user, get_user_by_email

logger = logging.getLogger(__name__)


def seed_default_manager_if_enabled(db: Session) -> bool:
    settings = get_settings()
    if not settings.seed_default_manager:
        return False

    existing_user = get_user_by_email(db, settings.default_manager_email)
    if existing_user:
        return False

    create_user(
        db,
        UserCreate(
            full_name=settings.default_manager_name,
            email=settings.default_manager_email,
            password=settings.default_manager_password,
            role=UserRole.MANAGER,
            is_active=True,
        ),
    )
    logger.info("Seeded default manager user: %s", settings.default_manager_email)
    return True
