"""Project REST API."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.errors import raise_service_error
from app.db.models import User
from app.db.session import get_db
from app.schemas.projects import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import projects as projects_svc
from app.services.errors import ServiceError

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProjectOut]:
    return [
        ProjectOut.model_validate(p)
        for p in projects_svc.list_projects(db, user.id)
    ]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectOut:
    row = projects_svc.create_project(
        db,
        user.id,
        name=body.name,
        description=body.description,
        persona=body.persona,
        icon=body.icon,
        memory_md=body.memory_md,
    )
    db.commit()
    db.refresh(row)
    return ProjectOut.model_validate(row)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectOut:
    try:
        row = projects_svc.get_project(db, user.id, project_id)
    except ServiceError as exc:
        raise_service_error(exc)
    return ProjectOut.model_validate(row)


@router.patch("/{project_id}", response_model=ProjectOut)
def patch_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectOut:
    try:
        row = projects_svc.update_project(
            db,
            user.id,
            project_id,
            name=body.name,
            description=body.description,
            persona=body.persona,
            icon=body.icon,
            memory_md=body.memory_md,
        )
        db.commit()
        db.refresh(row)
    except ServiceError as exc:
        raise_service_error(exc)
    return ProjectOut.model_validate(row)


@router.delete("/{project_id}", status_code=204, response_class=Response)
def delete_project(
    project_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        projects_svc.delete_project(db, user.id, project_id)
        db.commit()
    except ServiceError as exc:
        raise_service_error(exc)
    return Response(status_code=204)
