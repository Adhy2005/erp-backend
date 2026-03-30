"""
app/routes/users.py
--------------------
User profile and document endpoints. All routes require authentication.

  GET  /users/me                      — Return current user profile
  PATCH /users/me/profile             — Update department/designation/phone/address
  PATCH /users/me/preferences         — Update theme/workspace_enabled
  POST  /users/me/documents           — Upload a document record
  GET   /users/me/documents           — List all user documents
  DELETE /users/me/documents/{doc_id} — Delete a document (owner check)
"""

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.auth import get_current_user_db
from app.models.user_documents import UserDocument
from app.models.users import User
from app.schemas.documents import DocumentCreateRequest, DocumentResponse
from app.schemas.users import PreferencesUpdateRequest, ProfileUpdateRequest, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


# ── Step 6: User Profile Routes ───────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user_db)):
    """
    GET /users/me
    Returns the authenticated user's full profile.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role if isinstance(current_user.role, str) else current_user.role.value,
        is_active=current_user.is_active,
        department=current_user.department,
        designation=current_user.designation,
        join_date=current_user.join_date,
        phone=current_user.phone,
        address=current_user.address,
        theme=current_user.theme,
        workspace_enabled=current_user.workspace_enabled,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.get("/")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    """
    GET /users
    Returns a minimal list of all users in the system.
    """
    users = db.query(User).all()
    return [
        {
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
        }
        for u in users
    ]


@router.patch("/me/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db),
):
    """
    PATCH /users/me/profile
    Updates: department, designation, phone, address
    Only fields provided (non-None) are updated.
    """
    if payload.department is not None:
        current_user.department = payload.department
    if payload.designation is not None:
        current_user.designation = payload.designation
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.address is not None:
        current_user.address = payload.address

    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role if isinstance(current_user.role, str) else current_user.role.value,
        is_active=current_user.is_active,
        department=current_user.department,
        designation=current_user.designation,
        join_date=current_user.join_date,
        phone=current_user.phone,
        address=current_user.address,
        theme=current_user.theme,
        workspace_enabled=current_user.workspace_enabled,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.patch("/me/preferences", response_model=UserResponse)
def update_preferences(
    payload: PreferencesUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db),
):
    """
    PATCH /users/me/preferences
    Updates: theme, workspace_enabled
    Only fields provided (non-None) are updated.
    """
    if payload.theme is not None:
        current_user.theme = payload.theme
    if payload.workspace_enabled is not None:
        current_user.workspace_enabled = payload.workspace_enabled

    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role if isinstance(current_user.role, str) else current_user.role.value,
        is_active=current_user.is_active,
        department=current_user.department,
        designation=current_user.designation,
        join_date=current_user.join_date,
        phone=current_user.phone,
        address=current_user.address,
        theme=current_user.theme,
        workspace_enabled=current_user.workspace_enabled,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


# ── Step 7: User Document Routes ──────────────────────────────────────────────

@router.post("/me/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    payload: DocumentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db),
):
    """
    POST /users/me/documents
    Creates a new document record linked to the current user.
    """
    doc = UserDocument(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=payload.name,
        url=payload.url,
        uploaded_at=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return DocumentResponse(
        id=str(doc.id),
        user_id=str(doc.user_id),
        name=doc.name,
        url=doc.url,
        uploaded_at=doc.uploaded_at,
    )


@router.get("/me/documents", response_model=List[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db),
):
    """
    GET /users/me/documents
    Returns all documents uploaded by the current user.
    """
    docs = db.query(UserDocument).filter(UserDocument.user_id == current_user.id).all()
    return [
        DocumentResponse(
            id=str(d.id),
            user_id=str(d.user_id),
            name=d.name,
            url=d.url,
            uploaded_at=d.uploaded_at,
        )
        for d in docs
    ]


@router.delete("/me/documents/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db),
):
    """
    DELETE /users/me/documents/{doc_id}
    Deletes a document. Raises 404 if not found or not owned by user.
    """
    doc = db.query(UserDocument).filter(
        UserDocument.id == doc_id,
        UserDocument.user_id == current_user.id,
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully", "id": doc_id}
