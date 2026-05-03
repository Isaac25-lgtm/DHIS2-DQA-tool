from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Three-state DHIS2 status, surfaced to the frontend so it can render the right
# banner without making the user click "Test connection".
#
#   reachable      = DHIS2 base URL responds to a HEAD/GET; live sync is possible
#                    when a manager has signed in.
#   unreachable    = DHIS2 base URL does not respond (network outage or DHIS2 is
#                    down). The platform can still accept assessments and run
#                    analysis; only the live DHIS2 column will be empty until
#                    DHIS2 returns and someone clicks Sync.
#   not_configured = no DHIS2 base URL has been set. Operator action needed.
Dhis2Reachability = Literal["reachable", "unreachable", "not_configured"]


class Dhis2ConnectionStatus(BaseModel):
    connected: bool
    base_url: str
    last_checked_at: datetime
    message: str
    signed_in: bool = False
    # New 3-state field. The legacy `connected` field is kept for backwards
    # compatibility with existing frontend code paths.
    reachability: Dhis2Reachability = "not_configured"


class Dhis2LoginRequest(BaseModel):
    base_url: str | None = Field(default=None, max_length=255)
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=255)
