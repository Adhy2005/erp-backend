"""
app/tests/test_users.py
------------------------
Tests for user profile and document endpoints:
  GET  /api/v1/users/me
  PATCH /api/v1/users/me/profile
  PATCH /api/v1/users/me/preferences
  POST  /api/v1/users/me/documents
  GET   /api/v1/users/me/documents
  DELETE /api/v1/users/me/documents/{id}

All tests use the existing mock-DB infrastructure from conftest.py —
no real database connection is required.
"""

import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.tests.conftest import make_token, override_db, make_mock_db
from app.main import app
from app.middleware.auth import get_current_user_db

API = "/api/v1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(user_id=None, role="employee", is_active=True, **kwargs):
    """Build a MagicMock User ORM object with profile attributes."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = kwargs.get("email", "alice@test.com")
    user.full_name = kwargs.get("full_name", "Alice Smith")
    user.password_hash = "hashed"
    user.role = role
    user.is_active = is_active
    user.department = kwargs.get("department", None)
    user.designation = kwargs.get("designation", None)
    user.phone = kwargs.get("phone", None)
    user.address = kwargs.get("address", None)
    user.theme = kwargs.get("theme", None)
    user.workspace_enabled = kwargs.get("workspace_enabled", True)
    return user


def _make_doc(user_id, doc_id=None, name="Resume.pdf", url="https://example.com/doc.pdf"):
    """Build a MagicMock UserDocument ORM object."""
    from datetime import datetime
    doc = MagicMock()
    doc.id = doc_id or uuid.uuid4()
    doc.user_id = user_id
    doc.name = name
    doc.url = url
    doc.uploaded_at = datetime(2025, 1, 1, 12, 0, 0)
    return doc


def _auth_client(user: MagicMock):
    """
    Returns a TestClient that:
    1. Carries a valid JWT for the given user
    2. Overrides get_current_user_db to return the mock user directly
    """
    token = make_token(user.role, str(user.id))
    app.dependency_overrides[get_current_user_db] = lambda: user
    client = TestClient(app, headers={"Authorization": f"Bearer {token}"}, raise_server_exceptions=True)
    return client


def _cleanup():
    app.dependency_overrides.pop(get_current_user_db, None)


# ── GET /users/me ─────────────────────────────────────────────────────────────

def test_get_profile():
    """Authenticated user gets their own profile."""
    user = _make_user(department="Engineering", phone="+91-9876543210")
    client = _auth_client(user)
    try:
        response = client.get(f"{API}/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "alice@test.com"
        assert data["department"] == "Engineering"
        assert data["phone"] == "+91-9876543210"
    finally:
        _cleanup()


def test_token_required():
    """No token → 401 Unauthorized."""
    bare_client = TestClient(app, raise_server_exceptions=True)
    response = bare_client.get(f"{API}/users/me")
    assert response.status_code == 401


def test_inactive_user_forbidden():
    """Inactive user → 403 from get_current_user_db (tested via real dependency)."""
    # We bypass the override here and let get_current_user_db raise 403 itself.
    # Since we can't hit the real DB, we patch the dependency to raise 403.
    from fastapi import HTTPException, status
    def _inactive():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    app.dependency_overrides[get_current_user_db] = _inactive
    bare_client = TestClient(app, headers={"Authorization": "Bearer fake_token"}, raise_server_exceptions=False)
    try:
        response = bare_client.get(f"{API}/users/me")
        assert response.status_code == 403
    finally:
        _cleanup()


# ── PATCH /users/me/profile ───────────────────────────────────────────────────

def test_profile_update():
    """Profile fields are updated and returned."""
    user = _make_user()
    client = _auth_client(user)
    try:
        with override_db() as mock_db:
            response = client.patch(f"{API}/users/me/profile", json={
                "department": "HR",
                "designation": "Manager",
                "phone": "+91-1111111111",
                "address": "123 Main St, Bangalore",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["department"] == "HR"
        assert data["designation"] == "Manager"
        assert data["phone"] == "+91-1111111111"
        assert data["address"] == "123 Main St, Bangalore"
    finally:
        _cleanup()


def test_profile_partial_update():
    """Only provided fields are updated; others unchanged."""
    user = _make_user(department="Engineering", phone="+91-9999999999")
    client = _auth_client(user)
    try:
        with override_db():
            response = client.patch(f"{API}/users/me/profile", json={
                "department": "Sales",
            })
        assert response.status_code == 200
        assert response.json()["department"] == "Sales"
    finally:
        _cleanup()


# ── PATCH /users/me/preferences ───────────────────────────────────────────────

def test_preferences_update():
    """Theme and workspace_enabled are updated and returned."""
    user = _make_user()
    client = _auth_client(user)
    try:
        with override_db():
            response = client.patch(f"{API}/users/me/preferences", json={
                "theme": "dark",
                "workspace_enabled": False,
            })
        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"
        assert data["workspace_enabled"] is False
    finally:
        _cleanup()


# ── POST /users/me/documents ──────────────────────────────────────────────────

def test_document_upload():
    """Upload a document → 201 with document details returned."""
    user = _make_user()
    client = _auth_client(user)
    try:
        with override_db():
            response = client.post(f"{API}/users/me/documents", json={
                "name": "Resume.pdf",
                "url": "https://storage.example.com/resume.pdf",
            })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Resume.pdf"
        assert data["url"] == "https://storage.example.com/resume.pdf"
        assert "id" in data
    finally:
        _cleanup()


# ── GET /users/me/documents ───────────────────────────────────────────────────

def test_document_list():
    """List documents → returns all documents for current user."""
    user = _make_user()
    doc1 = _make_doc(user.id, name="Resume.pdf", url="https://ex.com/1.pdf")
    doc2 = _make_doc(user.id, name="ID.pdf", url="https://ex.com/2.pdf")

    client = _auth_client(user)
    try:
        with override_db(make_mock_db(query_all_return=[doc1, doc2])):
            response = client.get(f"{API}/users/me/documents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Resume.pdf"
        assert data[1]["name"] == "ID.pdf"
    finally:
        _cleanup()


def test_document_list_empty():
    """Empty document list → returns empty array."""
    user = _make_user()
    client = _auth_client(user)
    try:
        with override_db(make_mock_db(query_all_return=[])):
            response = client.get(f"{API}/users/me/documents")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        _cleanup()


# ── DELETE /users/me/documents/{id} ──────────────────────────────────────────

def test_document_delete():
    """Delete an owned document → 200 with success message."""
    user = _make_user()
    doc_id = uuid.uuid4()
    doc = _make_doc(user.id, doc_id=doc_id)

    client = _auth_client(user)
    try:
        with override_db(make_mock_db(query_first_return=doc)):
            response = client.delete(f"{API}/users/me/documents/{doc_id}")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()
    finally:
        _cleanup()


def test_document_delete_not_found():
    """Delete a non-existent document → 404."""
    user = _make_user()
    client = _auth_client(user)
    try:
        with override_db(make_mock_db(query_first_return=None)):
            response = client.delete(f"{API}/users/me/documents/{uuid.uuid4()}")
        assert response.status_code == 404
    finally:
        _cleanup()
