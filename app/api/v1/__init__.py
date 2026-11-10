"""API v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, chat, health, projects

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(chat.router)


__all__ = ["api_router"]
