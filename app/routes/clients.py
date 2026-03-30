"""
app/routes/clients.py
---------------------
CRM / Clients API routes.
  GET  /clients/     — List all clients
  POST /clients/     — Create a client
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.clients import Client

router = APIRouter(prefix="/clients", tags=["CRM / Clients"])


# ── Request schemas ────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str
    company: Optional[str] = ""
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = "active"


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/")
def list_clients(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all CRM clients."""
    clients = db.query(Client).order_by(Client.created_at.desc()).all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "company": c.company or "",
            "email": c.email,
            "phone": c.phone,
            "address": c.address,
            "status": c.status,
            "created_at": str(c.created_at) if c.created_at else None,
        }
        for c in clients
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new CRM client."""
    client = Client(
        id=uuid.uuid4(),
        name=data.name,
        company=data.company or "",
        email=data.email,
        phone=data.phone,
        address=data.address,
        status=data.status or "active",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return {
        "id": str(client.id),
        "name": client.name,
        "company": client.company,
        "email": client.email,
        "phone": client.phone,
        "address": client.address,
        "status": client.status,
        "created_at": str(client.created_at) if client.created_at else None,
    }
