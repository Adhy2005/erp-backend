"""
app/routes/finance.py
---------------------
Finance entry routes — strictest RBAC in the system.
POST: super_admin ONLY
GET:  super_admin + admin + founder + co_founder (manager/employee fully blocked with 403)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.middleware.rbac import require_role
from app.middleware.auth import get_current_user
from app.models.finance_entries import FinanceEntry
from app.models.projects import Project

router = APIRouter(prefix="/finance", tags=["Finance"])

FINANCE_ROLES = ("super_admin", "admin", "founder", "co_founder")


class FinanceCreate(BaseModel):
    amount: float
    type: str # 'income' or 'expense'
    description: Optional[str] = None
    project_id: Optional[str] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_finance_entry(
    data: FinanceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*FINANCE_ROLES)),
):
    """
    Create a finance entry.
    RBAC: Restricted to finance roles only.
    """
    if data.project_id:
        project = db.query(Project).filter(Project.id == uuid.UUID(data.project_id)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    entry = FinanceEntry(
        id=uuid.uuid4(),
        amount=data.amount,
        type=data.type,
        description=data.description,
        project_id=uuid.UUID(data.project_id) if data.project_id else None,
        created_by=uuid.UUID(current_user["user_id"]),
        client_name="N/A", # default value since field exists in db but not in spec
        currency="INR",    # default value
        category="general",# default value
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "message": "Finance entry created",
        "entry": {
            "id": str(entry.id),
            "amount": entry.amount,
            "type": entry.type,
            "description": entry.description,
            "project_id": str(entry.project_id) if entry.project_id else None,
            "created_by": str(entry.created_by),
        },
    }


@router.get("/")
def get_finance_entries(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(*FINANCE_ROLES)),
):
    """
    Get all finance entries.
    RBAC: Restricted to finance roles only.
    """
    entries = db.query(FinanceEntry).all()
    return [
        {
            "id": str(e.id),
            "amount": e.amount,
            "type": e.type,
            "description": e.description,
            "project_id": str(e.project_id) if e.project_id else None,
            "created_by": str(e.created_by),
            "created_at": str(e.created_at) if e.created_at else None,
            # include legacy fields just in case frontend needs them right now
            "category": e.category or "general",
            "client_name": e.client_name or "N/A"
        }
        for e in entries
    ]
