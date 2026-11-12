"""GET /models — danh sách model FE được chọn (không trả API key)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from agent.llm_providers import default_model_id, list_public_models
from app.api.deps import get_current_user
from app.db.models import User
from app.schemas.models import ModelListOut, ModelOut

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelListOut)
def list_models(
    _user: Annotated[User, Depends(get_current_user)],
) -> ModelListOut:
    items = [
        ModelOut(
            id=m.id,
            provider=m.provider,
            provider_label=m.provider_label,
            label=m.label,
            is_default=m.is_default,
        )
        for m in list_public_models()
    ]
    return ModelListOut(items=items, default=default_model_id())


__all__ = ["router"]
