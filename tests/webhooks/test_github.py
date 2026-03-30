import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

 
from main import app 
from app.db.session import get_db
from app.db.database import Base
from app.models.users import User
from app.models.projects import Project
from app.models.tasks import Task
from app.models.task_comments import TaskComment


from app.models.sprints import Sprint
from app.models.project_members import ProjectMember
from app.models.personal_workspace import PersonalWorkspace
from app.models.workspace_shared_users import WorkspaceSharedUser
from app.models.finance_entries import FinanceEntry
from app.models.user_documents import UserDocument

from sqlalchemy.pool import StaticPool
 
# ─── Test DB Setup ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite://" 
 
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
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
def seeded_project(db):
    """Seed a project matching the repo name used in payloads."""
    user = User(
        id=uuid.uuid4(),
        email="manager@example.com",
        password_hash="hashed_password",
        full_name="Manager",
        role="project_manager",
        is_active=True,
    )
    db.add(user)
    db.commit()
 
    project = Project(
        id=uuid.uuid4(),
        name="erp-backend",
        manager_id=user.id,
        status="active",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
 
 
@pytest.fixture
def seeded_task(db, seeded_project):
    """Seed a task for comment tests."""
    task = Task(
        id=uuid.uuid4(),
        title="Existing Task",
        project_id=seeded_project.id,
        status="todo",
        priority="medium",
        order_index=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
 
 
# ─── Pull Request Tests (Option A) ────────────────────────────────────────────
 
class TestGitHubPullRequestWebhook:
 
    # 1. SUCCESS — PR opened creates a task
    def test_pr_opened_creates_task(self, client, seeded_project, db):
        payload = {
            "action": "opened",
            "repository": {"name": "erp-backend"},
            "pull_request": {
                "title": "Fix login bug",
                "body": "Fixes the JWT expiry issue",
                "number": 42,
            }
        }
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "pull_request"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "task_created"
        assert "record_id" in data
 
        task = db.query(Task).filter(Task.title == "Fix login bug").first()
        assert task is not None
        assert task.project_id == seeded_project.id
 
    # 2. FAILURE — PR event but no matching project
    def test_pr_no_matching_project(self, client):
        payload = {
            "action": "opened",
            "repository": {"name": "unknown-repo"},
            "pull_request": {
                "title": "Some PR",
                "body": "body",
                "number": 1,
            }
        }
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "pull_request"},
        )
        assert response.status_code == 404
        assert "unknown-repo" in response.json()["detail"]
 
    # 3. FAILURE — PR event missing pull_request field
    def test_pr_missing_pull_request_field(self, client, seeded_project):
        payload = {
            "action": "opened",
            "repository": {"name": "erp-backend"},
            # pull_request field missing
        }
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "pull_request"},
        )
        assert response.status_code == 400
 
 
# ─── Push Tests (Option B) ────────────────────────────────────────────────────
 
class TestGitHubPushWebhook:
 
    # 4. SUCCESS — push adds comment to latest task
    def test_push_adds_comment(self, client, seeded_task, db):
        payload = {
            "ref": "refs/heads/main",
            "repository": {"name": "erp-backend"},
            "commits": [
                {"message": "Fix login bug"},
                {"message": "Add unit tests for auth"},
            ]
        }
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "comment_added"
 
        comment = db.query(TaskComment).filter(
            TaskComment.task_id == seeded_task.id
        ).first()
        assert comment is not None
        assert "Add unit tests for auth" in comment.text
 
    # 5. FAILURE — push with no commits
    def test_push_no_commits(self, client, seeded_project):
        payload = {
            "ref": "refs/heads/main",
            "repository": {"name": "erp-backend"},
            "commits": []
        }
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push"},
        )
        assert response.status_code == 400
 
    # 6. FAILURE — push but no tasks exist in project
    def test_push_no_tasks_in_project(self, client, seeded_project):
        payload = {
            "ref": "refs/heads/main",
            "repository": {"name": "erp-backend"},
            "commits": [{"message": "Initial commit"}]
        }
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push"},
        )
        assert response.status_code == 404
 
    # 7. FAILURE — missing X-GitHub-Event header
    def test_missing_github_event_header(self, client, seeded_project):
        payload = {
            "repository": {"name": "erp-backend"},
            "commits": [{"message": "test"}]
        }
        response = client.post("/webhooks/github", json=payload)
        assert response.status_code == 400
 
    # 8. FAILURE — unsupported event type
    def test_unsupported_event_type(self, client, seeded_project):
        payload = {
            "repository": {"name": "erp-backend"},
        }
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "star"},
        )
        assert response.status_code == 400