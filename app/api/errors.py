"""Map service errors to HTTPException."""

from __future__ import annotations

from fastapi import HTTPException

from app.services.errors import ServiceError


def raise_service_error(exc: ServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
