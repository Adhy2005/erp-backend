"""
app/routes/projects.py
-----------------------
Project API routes with RBAC enforcement.
"""

import uuid
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.middleware.rbac import require_role
from app.middleware.auth import get_current_user
from app.models.projects import Project
from app.models.project_members import ProjectMember

router = APIRouter(prefix="/projects", tags=["Projects"])


# ── Request schemas ────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "active"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AddMemberRequest(BaseModel):
    user_id: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "admin", "manager", "project_manager", "founder", "co_founder")),
):
    """
    Create a new project.
    manager_id is auto-set from the JWT — not accepted from body.
    RBAC: Only super_admin and project_manager allowed.
    """
    project = Project(
        id=uuid.uuid4(),
        name=data.name,
        description=data.description,
        manager_id=uuid.UUID(current_user["user_id"]),
        status=data.status or "active",
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "manager_id": str(project.manager_id),
        "status": str(project.status.value) if hasattr(project.status, 'value') else str(project.status),
        "start_date": str(project.start_date) if project.start_date else None,
        "end_date": str(project.end_date) if project.end_date else None,
        "created_at": str(project.created_at) if project.created_at else None,
        "updated_at": str(project.updated_at) if project.updated_at else None,
    }


@router.get("/")
def list_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all projects — returns full schema. All logged-in users can view."""
    projects = db.query(Project).all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "manager_id": str(p.manager_id) if p.manager_id else None,
            "status": str(p.status.value) if hasattr(p.status, 'value') else str(p.status),
            "start_date": str(p.start_date) if p.start_date else None,
            "end_date": str(p.end_date) if p.end_date else None,
            "created_at": str(p.created_at) if p.created_at else None,
            "updated_at": str(p.updated_at) if p.updated_at else None,
        }
        for p in projects
    ]


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: str,
    data: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "admin", "manager", "project_manager", "founder", "co_founder")),
):
    """Add a user to a project. RBAC: admin/manager only."""
    project = db.query(Project).filter(Project.id == uuid.UUID(project_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    member = ProjectMember(
        project_id=uuid.UUID(project_id),
        user_id=uuid.UUID(data.user_id),
    )
    db.add(member)
    db.commit()
    return {"message": "Member added", "project_id": project_id, "user_id": data.user_id}
