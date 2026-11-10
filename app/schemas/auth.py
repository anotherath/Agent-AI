"""Auth API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str = Field(min_length=3, max_length=320)
    email_verified: bool
    name: str | None
    avatar_url: str | None
    status: str
    last_login_at: datetime | None


class AuthMessage(BaseModel):
    status: str
    detail: str | None = None
