import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from main import app
from app.db.session import get_db
from app.db.database import Base
from app.models.users import User
from app.models.attendance_logs import AttendanceLog

from sqlalchemy.pool import StaticPool

 
# ─── Test DB setup (separate from prod) ────────────────────────────────────────
TEST_DATABASE_URL = "sqlite://"   # or a dedicated pg test DB
 
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine) 

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
 

app.dependency_overrides[get_db] = override_get_db
  
@pytest.fixture(autouse=True)
def setup_db():
    import app.models.users
    import app.models.projects
    import app.models.tasks
    import app.models.task_comments
    import app.models.attendance_logs
    import app.models.sprints
    import app.models.project_members
    import app.models.personal_workspace
    import app.models.workspace_shared_users
    import app.models.finance_entries
    import app.models.user_documents
    
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    
 
 
@pytest.fixture
def client():
    return TestClient(app)
 
 
@pytest.fixture
def db():
    session = TestingSessionLocal()

    def override():
        yield session

    app.dependency_overrides[get_db] = override
    yield session
    session.close()
    app.dependency_overrides[get_db] = override_get_db
 
 
@pytest.fixture
def active_user(db):
    """Seed an active user for webhook lookup."""
    user = User(
        email="jibble_user@example.com",
         password_hash="hashed_password", 
        full_name="Jibble User",
        role="employee",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
 
 
# ─── Test Cases ────────────────────────────────────────────────────────────────
 
class TestJibbleWebhook:
 
    # 1. SUCCESS CASE
    def test_jibble_clock_in_success(self, client, active_user, db):
        payload = {
            "email": "jibble_user@example.com",
            "clock_in": "2024-01-15T09:00:00",
            "clock_out": "2024-01-15T17:00:00",
            "source": "jibble",
        }
        response = client.post("/webhooks/jibble", json=payload)
 
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Attendance log recorded successfully"
        assert "attendance_id" in data
 
        # Verify it was actually inserted
        log = db.query(AttendanceLog).filter(
            AttendanceLog.user_id == active_user.id
        ).first()
        assert log is not None
        assert str(log.source) == "jibble"
 
    # 2. CLOCK-IN ONLY (no clock_out) — valid
    def test_jibble_clock_in_only(self, client, active_user):
        payload = {
            "email": "jibble_user@example.com",
            "clock_in": "2024-01-15T09:00:00",
            "source": "jibble",
        }
        response = client.post("/webhooks/jibble", json=payload)
        assert response.status_code == 201
 
    # 3. FAILURE — user not found
    def test_jibble_user_not_found(self, client):
        payload = {
            "email": "ghost@example.com",
            "clock_in": "2024-01-15T09:00:00",
            "source": "jibble",
        }
        response = client.post("/webhooks/jibble", json=payload)
        assert response.status_code == 404
        assert "ghost@example.com" in response.json()["detail"]
 
    # 4. FAILURE — invalid payload (missing clock_in)
    def test_jibble_invalid_payload_missing_clock_in(self, client):
        payload = {
            "email": "jibble_user@example.com",
            "source": "jibble",
            # clock_in intentionally missing
        }
        response = client.post("/webhooks/jibble", json=payload)
        assert response.status_code == 422   # Pydantic validation error
 
    # 5. FAILURE — clock_out before clock_in
    def test_jibble_clock_out_before_clock_in(self, client, active_user):
        payload = {
            "email": "jibble_user@example.com",
            "clock_in": "2024-01-15T17:00:00",
            "clock_out": "2024-01-15T09:00:00",   # before clock_in
            "source": "jibble",
        }
        response = client.post("/webhooks/jibble", json=payload)
        assert response.status_code == 422
 
    # 6. FK VIOLATION — inactive user blocked
    def test_jibble_inactive_user_blocked(self, client, db):
        inactive_user = User(
            email="inactive@example.com",
            password_hash="hashed_password",
            full_name="Inactive",
            role="employee",
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()
 
        payload = {
            "email": "inactive@example.com",
            "clock_in": "2024-01-15T09:00:00",
            "source": "jibble",
        }
        response = client.post("/webhooks/jibble", json=payload)
        assert response.status_code == 404   # treated same as not found