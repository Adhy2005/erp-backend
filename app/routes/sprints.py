"""
app/routes/sprints.py
---------------------
Sprint API routes.
Validates project_id FK exists before creating a sprint.
"""

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.middleware.rbac import require_role
from app.middleware.auth import get_current_user
from app.models.sprints import Sprint
from app.models.projects import Project

router = APIRouter(prefix="/sprints", tags=["Sprints"])


class SprintCreate(BaseModel):
    project_id: str
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_sprint(
    data: SprintCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "project_manager")),
):
    """
    Create a sprint.
    FK check: project_id must exist — returns 404 if it doesn't.
    """
    project = db.query(Project).filter(Project.id == uuid.UUID(data.project_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found")

    sprint = Sprint(
        id=uuid.uuid4(),
        project_id=uuid.UUID(data.project_id),
        name=data.name,
        is_active=False,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return {
        "id": str(sprint.id),
        "project_id": str(sprint.project_id),
        "name": sprint.name,
        "is_active": sprint.is_active,
        "start_date": str(sprint.start_date) if sprint.start_date else None,
        "end_date": str(sprint.end_date) if sprint.end_date else None,
        "created_at": str(sprint.created_at) if sprint.created_at else None,
        "updated_at": str(sprint.updated_at) if sprint.updated_at else None,
    }


@router.patch("/{sprint_id}/activate")
def activate_sprint(
    sprint_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "project_manager")),
):
    """
    Activate a sprint — sets is_active=True on this sprint,
    sets is_active=False on all other sprints in the same project.
    """
    sprint = db.query(Sprint).filter(Sprint.id == uuid.UUID(sprint_id)).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    # Deactivate all other sprints in same project
    db.query(Sprint).filter(
        Sprint.project_id == sprint.project_id,
        Sprint.id != sprint.id,
    ).update({"is_active": False})

    sprint.is_active = True
    db.commit()
    return {"message": "Sprint activated", "sprint_id": sprint_id}


@router.get("/")
def list_sprints(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all sprints with full schema."""
    sprints = db.query(Sprint).all()
    return [
        {
            "id": str(s.id),
            "project_id": str(s.project_id),
            "name": s.name,
            "is_active": s.is_active,
            "start_date": str(s.start_date) if s.start_date else None,
            "end_date": str(s.end_date) if s.end_date else None,
            "created_at": str(s.created_at) if s.created_at else None,
            "updated_at": str(s.updated_at) if s.updated_at else None,
        }
        for s in sprints
    ]
