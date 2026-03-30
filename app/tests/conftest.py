"""
tests/conftest.py
-----------------
Shared test utilities using sync SQLAlchemy mock.
Tests run without any real database connection.
"""

import uuid
import os

# Set fake env vars BEFORE any imports so SQLAlchemy engine is never created
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "postgresql://fake:fake@localhost/fake"

from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from fastapi.testclient import TestClient

# Patch create_engine at the SQLAlchemy level so database.py never connects
_engine_mock = MagicMock()
_session_mock = MagicMock()
with patch("sqlalchemy.create_engine", return_value=_engine_mock), \
     patch("sqlalchemy.orm.sessionmaker", return_value=_session_mock):
    from app.main import app

from app.db.session import get_db
from app.middleware.auth import create_access_token


# ── Token helper ───────────────────────────────────────────────────────────────

def make_token(role: str, user_id: str = None) -> str:
    """Creates a real signed JWT for any role."""
    if user_id is None:
        user_id = str(uuid.uuid4())
    return create_access_token({
        "sub": f"{role}@test.com",
        "role": role,
        "user_id": user_id,
    })


# ── Mock DB session builder ────────────────────────────────────────────────────

def make_mock_db(query_first_return=None, query_all_return=None):
    """
    Builds a fake synchronous SQLAlchemy Session.
    query_first_return → what db.query(...).filter(...).first() returns
    query_all_return   → what db.query(...).all() / .filter(...).all() returns
    """
    db = MagicMock()

    # db.query(Model).filter(...).first() chain
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = query_first_return
    filter_mock.all.return_value = query_all_return if query_all_return is not None else []
    query_mock.filter.return_value = filter_mock
    query_mock.all.return_value = query_all_return if query_all_return is not None else []
    db.query.return_value = query_mock

    # db.get(Model, id) — for direct pk lookup
    db.get.return_value = query_first_return

    return db


# ── Context manager for session override ──────────────────────────────────────

@contextmanager
def override_db(mock_db=None):
    """
    Use in tests to inject a mock DB session:
        with override_db(make_mock_db(query_first_return=fake_obj)):
            response = get_client("super_admin").post(...)
    """
    if mock_db is None:
        mock_db = make_mock_db()

    def _mock_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _mock_get_db
    try:
        yield mock_db
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Test client builder ────────────────────────────────────────────────────────

FIXED_USER_ID = str(uuid.uuid4())

def get_client(role: str, user_id: str = None):
    """Returns a TestClient pre-authenticated with the given role."""
    uid = user_id or FIXED_USER_ID
    token = make_token(role, uid)
    return TestClient(
        app,
        headers={"Authorization": f"Bearer {token}"},
        raise_server_exceptions=True,
    )
