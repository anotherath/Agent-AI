"""LLM catalog API schemas (FE list / pick model)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelOut(BaseModel):
    id: str = Field(description="Catalog id: provider:model")
    provider: str
    provider_label: str
    label: str
    is_default: bool = False


class ModelListOut(BaseModel):
    items: list[ModelOut]
    default: str


__all__ = ["ModelOut", "ModelListOut"]
