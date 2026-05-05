from __future__ import annotations

import logging
import uuid

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


def log_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    description: str,
    actor_user_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    request: Request | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=_truncate(request.client.host if request and request.client else None, 64),
        user_agent=_truncate(request.headers.get("user-agent") if request else None, 255),
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def try_log_audit_event(db: Session, **kwargs) -> AuditLog | None:
    """Best-effort audit logging for auth paths.

    Login must never fail just because audit storage is temporarily unavailable
    or an older production schema is being repaired by migrations.
    """
    try:
        with db.begin_nested():
            return log_audit_event(db, **kwargs)
    except SQLAlchemyError:
        logger.exception("Audit logging skipped after database error.")
        return None
