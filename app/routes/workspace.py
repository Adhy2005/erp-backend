"""
app/routes/workspace.py
------------------------
Personal workspace routes — private notes with sharing between users.
Ownership enforced: only owner can edit or delete.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.personal_workspace import PersonalWorkspace
from app.models.workspace_shared_users import WorkspaceSharedUser

router = APIRouter(prefix="/workspace", tags=["Personal Workspace"])


class WorkspaceCreate(BaseModel):
    title: str
    content: Optional[str] = None
    is_shared: bool = False
    shared_with: List[str] = []     # list of user_id UUIDs to share with


class WorkspaceUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_shared: Optional[bool] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_workspace_item(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a personal workspace item. Owner = current logged-in user."""
    item = PersonalWorkspace(
        id=uuid.uuid4(),
        owner_id=uuid.UUID(current_user["user_id"]),
        title=data.title,
        content=data.content,
        is_shared=data.is_shared,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Add sharing rows for each user in shared_with list
    for uid in data.shared_with:
        share = WorkspaceSharedUser(
            id=uuid.uuid4(),
            workspace_id=item.id,
            shared_with_user_id=uuid.UUID(uid),
        )
        db.add(share)
    db.commit()

    return {"message": "Workspace item created", "item_id": str(item.id)}


@router.get("/")
def get_my_workspace(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Returns items owned by the user + items shared with the user."""
    uid = uuid.UUID(current_user["user_id"])

    # Items I own
    my_items = db.query(PersonalWorkspace).filter(PersonalWorkspace.owner_id == uid).all()

    # Items shared with me
    shared_ids = [
        s.workspace_id for s in
        db.query(WorkspaceSharedUser).filter(WorkspaceSharedUser.shared_with_user_id == uid).all()
    ]
    shared_items = db.query(PersonalWorkspace).filter(PersonalWorkspace.id.in_(shared_ids)).all()

    all_items = my_items + [i for i in shared_items if i not in my_items]
    return [{"id": str(i.id), "title": i.title, "owner_id": str(i.owner_id)} for i in all_items]


@router.patch("/{item_id}")
def update_workspace_item(
    item_id: str,
    data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update workspace item — only the owner can edit."""
    item = db.query(PersonalWorkspace).filter(PersonalWorkspace.id == uuid.UUID(item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if str(item.owner_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only edit your own workspace items")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    return {"message": "Item updated", "item_id": item_id}


@router.delete("/{item_id}")
def delete_workspace_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete workspace item — only the owner can delete."""
    item = db.query(PersonalWorkspace).filter(PersonalWorkspace.id == uuid.UUID(item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if str(item.owner_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own workspace items")

    db.delete(item)
    db.commit()
    return {"message": "Item deleted", "item_id": item_id}
