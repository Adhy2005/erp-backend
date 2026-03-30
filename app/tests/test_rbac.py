"""tests/test_rbac.py — RBAC enforcement tests"""
import uuid
from app.tests.conftest import get_client, override_db, make_mock_db, FIXED_USER_ID


class TestEmployeeBlocked:

    def test_employee_cannot_delete_task(self):
        """Employee → DELETE /tasks/{id} → 403."""
        fake_task = type("Task", (), {"id": uuid.uuid4(), "assignee_id": uuid.uuid4()})()
        with override_db(make_mock_db(query_first_return=fake_task)):
            r = get_client("employee").delete(f"/api/v1/tasks/{uuid.uuid4()}")
        assert r.status_code == 403

    def test_employee_cannot_create_project(self):
        """Employee → POST /projects/ → 403."""
        with override_db():
            r = get_client("employee").post(
                "/api/v1/projects/",
                json={"name": "Test", "manager_id": str(uuid.uuid4())},
            )
        assert r.status_code == 403

    def test_employee_cannot_post_finance(self):
        """Employee → POST /finance/ → 403."""
        with override_db():
            r = get_client("employee").post(
                "/api/v1/finance/",
                json={"type": "subscription", "amount": 100.0, "client_name": "Test Co"},
            )
        assert r.status_code == 403

    def test_employee_cannot_get_finance(self):
        """Employee → GET /finance/ → 403."""
        with override_db():
            r = get_client("employee").get("/api/v1/finance/")
        assert r.status_code == 403


class TestEmployeeOwnership:

    def test_employee_cannot_edit_others_task(self):
        """Employee edits a task assigned to someone else → 403."""
        other_user_id = uuid.uuid4()
        fake_task = type("Task", (), {
            "id": uuid.uuid4(),
            "assignee_id": other_user_id,   # belongs to someone else
        })()
        with override_db(make_mock_db(query_first_return=fake_task)):
            r = get_client("employee", user_id=FIXED_USER_ID).patch(
                f"/api/v1/tasks/{fake_task.id}",
                json={"title": "Hacked"},
            )
        assert r.status_code == 403

    def test_employee_can_edit_own_task(self):
        """Employee edits their own task → 200."""
        fake_task = type("Task", (), {
            "id": uuid.uuid4(),
            "assignee_id": uuid.UUID(FIXED_USER_ID),  # belongs to THIS user
        })()
        with override_db(make_mock_db(query_first_return=fake_task)):
            r = get_client("employee", user_id=FIXED_USER_ID).patch(
                f"/api/v1/tasks/{fake_task.id}",
                json={"title": "My own update"},
            )
        assert r.status_code == 200


class TestManagerAndAdminAllowed:

    def test_manager_can_create_project(self):
        """Manager → POST /projects/ → 201."""
        with override_db():
            r = get_client("project_manager").post(
                "/api/v1/projects/",
                json={"name": "New Project", "manager_id": str(uuid.uuid4())},
            )
        assert r.status_code == 201

    def test_admin_can_delete_task(self):
        """Admin → DELETE /tasks/{id} on existing task → 200."""
        fake_task = type("Task", (), {"id": uuid.uuid4(), "assignee_id": uuid.uuid4()})()
        with override_db(make_mock_db(query_first_return=fake_task)):
            r = get_client("super_admin").delete(f"/api/v1/tasks/{fake_task.id}")
        assert r.status_code == 200
