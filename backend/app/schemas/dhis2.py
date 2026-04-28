from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Dhis2ConnectionStatus(BaseModel):
    connected: bool
    base_url: str
    last_checked_at: datetime
    message: str
    signed_in: bool = False


class Dhis2LoginRequest(BaseModel):
    base_url: str | None = Field(default=None, max_length=255)
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=255)
