"""Project CRUD scoped to owning user."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatSession, Project
from app.services.errors import ConflictError, NotFoundError


def list_projects(db: Session, user_id: uuid.UUID) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.updated_at.desc())
        ).all()
    )


def get_project(db: Session, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    if project is None:
        raise NotFoundError("Project not found")
    return project


def create_project(
    db: Session,
    user_id: uuid.UUID,
    *,
    name: str,
    description: str | None = None,
    persona: str | None = None,
    icon: str = "folder",
    memory_md: str | None = None,
) -> Project:
    project = Project(
        user_id=user_id,
        name=name.strip(),
        description=description,
        persona=persona,
        icon=(icon or "folder").strip() or "folder",
        memory_md=memory_md,
    )
    db.add(project)
    db.flush()
    return project


def update_project(
    db: Session,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    persona: str | None = None,
    icon: str | None = None,
    memory_md: str | None = None,
) -> Project:
    project = get_project(db, user_id, project_id)
    if name is not None:
        project.name = name.strip()
    if description is not None:
        project.description = description
    if persona is not None:
        project.persona = persona
    if icon is not None:
        project.icon = icon.strip() or "folder"
    if memory_md is not None:
        project.memory_md = memory_md
    project.updated_at = datetime.now(UTC)
    db.add(project)
    db.flush()
    return project


def delete_project(db: Session, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
    project = get_project(db, user_id, project_id)
    linked = db.scalar(
        select(ChatSession.id).where(ChatSession.project_id == project_id).limit(1)
    )
    if linked is not None:
        raise ConflictError("Project still has chat sessions; detach is not allowed")
    db.delete(project)
    db.flush()
