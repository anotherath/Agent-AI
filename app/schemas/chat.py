"""Chat session / message API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    title: str | None = None
    project_id: uuid.UUID | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = None


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    title: str | None
    is_main: bool
    is_pinned: bool
    pinned_at: datetime | None
    run_status: Literal["idle", "running", "completed", "error"] = "idle"
    active_run_id: uuid.UUID | None = None
    last_read_at: datetime | None = None
    last_message_at: datetime | None = None
    has_unread: bool = False
    parent_session_id: uuid.UUID | None
    forked_from_message_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ChatSessionListOut(BaseModel):
    items: list[ChatSessionOut]
    total: int
    limit: int
    offset: int
    has_more: bool


class ForkRequest(BaseModel):
    forked_from_message_id: uuid.UUID
    title: str | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    parent_message_id: uuid.UUID | None = None
    role: str
    content: str
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime


class MessageRegenerateRequest(BaseModel):
    """Optional override; default = latest user message on the session."""

    user_message_id: uuid.UUID | None = None


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    file_ids: list[uuid.UUID] | None = None  # reserved; ignored this phase


class MessageEditRequest(BaseModel):
    content: str = Field(min_length=1)


class AskFromSelectionRequest(BaseModel):
    message_id: uuid.UUID
    selected_text: str = Field(min_length=1)
    question: str = Field(min_length=1)
    target: Literal["main", "subsession"]
