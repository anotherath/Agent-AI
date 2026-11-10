"""Project API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Đồng bộ với ui-ai-rag/lib/project-icons.ts ProjectIconId.
ProjectIconId = Literal[
    "folder",
    "file",
    "briefcase",
    "scale",
    "sparkles",
    "code",
    "book",
    "grad",
    "heart",
    "bulb",
    "rocket",
    "globe",
    "bot",
    "palette",
    "music",
    "camera",
    "beaker",
    "stethoscope",
    "terminal",
    "image",
]

DEFAULT_PROJECT_ICON: ProjectIconId = "folder"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    persona: str | None = None
    icon: ProjectIconId = DEFAULT_PROJECT_ICON
    memory_md: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    persona: str | None = None
    icon: ProjectIconId | None = None
    memory_md: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    persona: str | None
    icon: str
    memory_md: str | None
    created_at: datetime
    updated_at: datetime
