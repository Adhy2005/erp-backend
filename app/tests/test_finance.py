"""tests/test_finance.py — Finance RBAC access tests"""
import uuid
from app.tests.conftest import get_client, override_db, make_mock_db


class TestFinanceRBAC:

    def test_employee_cannot_get_finance(self):
        with override_db():
            r = get_client("employee").get("/api/v1/finance/")
        assert r.status_code == 403

    def test_employee_cannot_post_finance(self):
        with override_db():
            r = get_client("employee").post(
                "/api/v1/finance/",
                json={"type": "subscription", "amount": 500.0, "client_name": "Co"},
            )
        assert r.status_code == 403

    def test_project_manager_can_get_finance(self):
        with override_db(make_mock_db(query_all_return=[])):
            r = get_client("project_manager").get("/api/v1/finance/")
        assert r.status_code == 200

    def test_project_manager_cannot_post_finance(self):
        with override_db():
            r = get_client("project_manager").post(
                "/api/v1/finance/",
                json={"type": "one-time", "amount": 1000.0, "client_name": "Corp"},
            )
        assert r.status_code == 403

    def test_super_admin_can_get_finance(self):
        with override_db(make_mock_db(query_all_return=[])):
            r = get_client("super_admin").get("/api/v1/finance/")
        assert r.status_code == 200

    def test_super_admin_can_create_finance(self):
        with override_db():
            r = get_client("super_admin").post(
                "/api/v1/finance/",
                json={"type": "subscription", "amount": 9999.0, "client_name": "Big Corp"},
            )
        assert r.status_code == 201
