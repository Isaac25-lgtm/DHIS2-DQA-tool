from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ManagerNotificationResponse(BaseModel):
    id: UUID
    action: str
    title: str
    message: str
    entity_type: str
    entity_id: UUID | None
    description: str
    actor_user_id: UUID | None
    actor_name: str | None
    created_at: datetime


class ManagerNotificationMarkSeenRequest(BaseModel):
    notification_ids: list[UUID]


class ManagerNotificationMarkSeenResponse(BaseModel):
    marked_seen: int
