"""tests/test_projects.py — FK validation, comments, workspace ownership tests"""
import uuid
from app.tests.conftest import get_client, override_db, make_mock_db, FIXED_USER_ID


class TestFKValidation:

    def test_sprint_with_invalid_project_id(self):
        """Sprint with non-existent project_id → 404."""
        with override_db(make_mock_db(query_first_return=None)):   # project not found
            r = get_client("project_manager").post(
                "/api/v1/sprints/",
                json={"project_id": str(uuid.uuid4()), "name": "Sprint 1"},
            )
        assert r.status_code == 404

    def test_sprint_with_valid_project_id(self):
        """Sprint with valid project_id → 201."""
        fake_project = type("Project", (), {"id": uuid.uuid4(), "name": "Real Project"})()
        with override_db(make_mock_db(query_first_return=fake_project)):
            r = get_client("project_manager").post(
                "/api/v1/sprints/",
                json={"project_id": str(fake_project.id), "name": "Sprint 1"},
            )
        assert r.status_code == 201


class TestComments:

    def test_add_comment_to_existing_task(self):
        """POST /tasks/{id}/comments on existing task → 201."""
        fake_task = type("Task", (), {"id": uuid.uuid4()})()
        with override_db(make_mock_db(query_first_return=fake_task)):
            r = get_client("employee", user_id=FIXED_USER_ID).post(
                f"/api/v1/tasks/{fake_task.id}/comments",
                json={"content": "Looks good!"},
            )
        assert r.status_code == 201

    def test_add_comment_to_missing_task(self):
        """POST /tasks/{id}/comments on missing task → 404."""
        with override_db(make_mock_db(query_first_return=None)):
            r = get_client("employee").post(
                f"/api/v1/tasks/{uuid.uuid4()}/comments",
                json={"content": "Hello?"},
            )
        assert r.status_code == 404


class TestWorkspaceOwnership:

    def test_owner_can_delete_own_item(self):
        """Owner deletes their own workspace item → 200."""
        fake_item = type("Item", (), {"id": uuid.uuid4(), "owner_id": uuid.UUID(FIXED_USER_ID)})()
        with override_db(make_mock_db(query_first_return=fake_item)):
            r = get_client("employee", user_id=FIXED_USER_ID).delete(
                f"/api/v1/workspace/{fake_item.id}"
            )
        assert r.status_code == 200

    def test_non_owner_cannot_delete_item(self):
        """Non-owner tries to delete someone else's workspace item → 403."""
        owner_id = uuid.uuid4()
        fake_item = type("Item", (), {"id": uuid.uuid4(), "owner_id": owner_id})()
        # current user is FIXED_USER_ID which is different from owner_id
        with override_db(make_mock_db(query_first_return=fake_item)):
            r = get_client("employee", user_id=FIXED_USER_ID).delete(
                f"/api/v1/workspace/{fake_item.id}"
            )
        assert r.status_code == 403
