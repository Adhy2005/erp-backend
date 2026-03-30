"""
app/tests/test_auth.py
-----------------------
Tests for authentication endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/oauth

All tests use the existing mock-DB infrastructure from conftest.py —
no real database connection is required.
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# conftest.py sets env vars and patches create_engine before any import
from app.tests.conftest import make_mock_db, override_db

# Import the app AFTER conftest has already patched the engine
from app.main import app

API = "/api/v1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_user(email="alice@test.com", password_hash=None, role="employee", is_active=True):
    """Build a MagicMock that looks like a User ORM object."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.password_hash = password_hash or pwd.hash("secret123")
    user.full_name = "Alice Smith"
    user.role = role
    user.is_active = is_active
    user.department = None
    user.designation = None
    user.phone = None
    user.address = None
    user.theme = None
    user.workspace_enabled = True
    return user


client = TestClient(app, raise_server_exceptions=True)


# ── Step 1: Register tests ────────────────────────────────────────────────────

def test_register_success():
    """New email → 201 + access_token returned."""
    with override_db(make_mock_db(query_first_return=None)):
        response = client.post(f"{API}/auth/register", json={
            "email": "newuser@test.com",
            "password": "pass1234",
            "full_name": "New User",
            "role": "employee",
        })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["email"] == "newuser@test.com"


def test_duplicate_email():
    """Existing email → 400 Bad Request."""
    existing = _fake_user(email="duplicate@test.com")
    with override_db(make_mock_db(query_first_return=existing)):
        response = client.post(f"{API}/auth/register", json={
            "email": "duplicate@test.com",
            "password": "pass1234",
            "full_name": "Dup User",
            "role": "employee",
        })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_register_short_password():
    """Password shorter than 6 chars → 422 Unprocessable Entity."""
    with override_db(make_mock_db(query_first_return=None)):
        response = client.post(f"{API}/auth/register", json={
            "email": "x@test.com",
            "password": "abc",
            "full_name": "X User",
            "role": "employee",
        })
    assert response.status_code == 422


# ── Step 2: Login tests ───────────────────────────────────────────────────────

def test_login_success():
    """Correct credentials → 200 + access_token."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = _fake_user(email="alice@test.com", password_hash=pwd.hash("secret123"))

    with override_db(make_mock_db(query_first_return=user)):
        response = client.post(f"{API}/auth/login", json={
            "email": "alice@test.com",
            "password": "secret123",
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["email"] == "alice@test.com"


def test_login_invalid_password():
    """Wrong password → 401 Unauthorized."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = _fake_user(email="alice@test.com", password_hash=pwd.hash("secret123"))

    with override_db(make_mock_db(query_first_return=user)):
        response = client.post(f"{API}/auth/login", json={
            "email": "alice@test.com",
            "password": "wrongpassword",
        })
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_login_user_not_found():
    """Non-existent email → 401 Unauthorized."""
    with override_db(make_mock_db(query_first_return=None)):
        response = client.post(f"{API}/auth/login", json={
            "email": "ghost@test.com",
            "password": "anypassword",
        })
    assert response.status_code == 401


# ── Step 3: OAuth tests ───────────────────────────────────────────────────────

def test_oauth_user_creation():
    """No existing user → creates new user and returns token."""
    with override_db(make_mock_db(query_first_return=None)):
        response = client.post(f"{API}/auth/oauth", json={
            "email": "newjibble@test.com",
            "full_name": "Jibble User",
            "provider": "jibble",
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["email"] == "newjibble@test.com"


def test_oauth_existing_user():
    """Existing user found → returns token without creating a new user."""
    existing = _fake_user(email="oldjibble@test.com")
    with override_db(make_mock_db(query_first_return=existing)):
        response = client.post(f"{API}/auth/oauth", json={
            "email": "oldjibble@test.com",
            "full_name": "Jibble User",
            "provider": "jibble",
        })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_token_protected_route_without_token():
    """Hitting a protected route with no token → 401."""
    response = client.get(f"{API}/users/me")
    assert response.status_code == 401
