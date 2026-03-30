# My Week 1 Submission — Leelavathi

## Task Assigned

Build RBAC (Role-Based Access Control) and all API routes for the ERP backend.  
Database models were done by a teammate. I built authentication, role enforcement, and the API layer on top.

---

## Exact Work Done

### 1. Authentication (`app/middleware/auth.py`)

- Built JWT token system — when a user logs in, they get a signed token
- Every API call sends this token in the header
- My code reads it and extracts: who they are, what role they have, their user ID
- If token is invalid or missing → returns **401 Unauthorized**

### 2. Role-Based Access Control (`app/middleware/rbac.py`)

- Built a `require_role()` function that acts as a gate on any route
- Before the route runs: checks if user's role is in the allowed list
- If not → returns **403 Forbidden** instantly, without touching the database
- Three roles: `super_admin`, `project_manager`, `employee`

### 3. Database Session Provider (`app/db/session.py`)

- Built `get_db()` — gives each route a database session and auto-closes it after

### 4. App Entry Point (`app/main.py`)

- Created the FastAPI app, added CORS for frontend, registered all 5 route files

### 5. Projects API (`app/routes/projects.py`)

- `POST /api/v1/projects/` — Create project (admin/manager only, employee → 403)
- `GET /api/v1/projects/` — List all projects (all logged-in users)
- `POST /api/v1/projects/{id}/members` — Add member to project (admin/manager only)

### 6. Sprints API (`app/routes/sprints.py`)

- `POST /api/v1/sprints/` — Create sprint (checks project_id exists first, else 404)
- `PATCH /api/v1/sprints/{id}/activate` — Activate sprint (admin/manager only)

### 7. Tasks API (`app/routes/tasks.py`)

- `POST /api/v1/tasks/` — Create task (validates project, sprint, parent task all exist)
- `PATCH /api/v1/tasks/{id}` — Update task (employee: only their own tasks, else 403)
- `DELETE /api/v1/tasks/{id}` — Delete task (admin/manager only, employee → 403)
- `POST /api/v1/tasks/{id}/comments` — Add comment to a task
- `GET /api/v1/tasks/{id}/comments` — Get all comments on a task

### 8. Personal Workspace API (`app/routes/workspace.py`)

- `POST /api/v1/workspace/` — Create a private note (owner = logged-in user)
- `GET /api/v1/workspace/` — List own notes + notes shared with me
- `PATCH /api/v1/workspace/{id}` — Edit note (owner only, else 403)
- `DELETE /api/v1/workspace/{id}` — Delete note (owner only, else 403)

### 9. Finance API (`app/routes/finance.py`)

- `POST /api/v1/finance/` — Create finance entry (super_admin ONLY)
- `GET /api/v1/finance/` — Read entries (admin + manager only, employee → 403)

### 10–13. Automated Tests (`tests/`)

- `conftest.py` — Fake database session so tests run without real PostgreSQL
- `test_rbac.py` — 8 tests for role blocking/allowing
- `test_projects.py` — 6 tests for FK checks, comments, workspace ownership
- `test_finance.py` — 6 tests for finance access per role

---

## Files I Added (Summary)

```
app/main.py
app/db/session.py
app/middleware/auth.py
app/middleware/rbac.py
app/routes/projects.py
app/routes/sprints.py
app/routes/tasks.py
app/routes/workspace.py
app/routes/finance.py
tests/conftest.py
tests/test_rbac.py
tests/test_projects.py
tests/test_finance.py
```

Total: **13 new files**

---

## How I Checked That the Code Works

Since the database was not ready, I wrote tests that use a **mock (fake) database**.  
Instead of connecting to PostgreSQL, the tests inject a fake session using `dependency_overrides`.  
This lets us check RBAC rules, FK validations, and ownership checks — all without a real database.

**Command to run:**

```bash
cd "C:\Users\...\enterprise-resource-planning-main\backend"
python -m pytest tests/ -v
```

**Output — 20 tests all passed:**

```
tests/test_finance.py::test_employee_cannot_get_finance        PASSED
tests/test_finance.py::test_employee_cannot_post_finance       PASSED
tests/test_finance.py::test_project_manager_can_get_finance    PASSED
tests/test_finance.py::test_project_manager_cannot_post_finance PASSED
tests/test_finance.py::test_super_admin_can_get_finance        PASSED
tests/test_finance.py::test_super_admin_can_create_finance     PASSED
tests/test_projects.py::test_sprint_with_invalid_project_id   PASSED
tests/test_projects.py::test_sprint_with_valid_project_id     PASSED
tests/test_projects.py::test_add_comment_to_existing_task     PASSED
tests/test_projects.py::test_add_comment_to_missing_task      PASSED
tests/test_projects.py::test_owner_can_delete_own_item        PASSED
tests/test_projects.py::test_non_owner_cannot_delete_item     PASSED
tests/test_rbac.py::test_employee_cannot_delete_task          PASSED
tests/test_rbac.py::test_employee_cannot_create_project       PASSED
tests/test_rbac.py::test_employee_cannot_post_finance         PASSED
tests/test_rbac.py::test_employee_cannot_get_finance          PASSED
tests/test_rbac.py::test_employee_cannot_edit_others_task     PASSED
tests/test_rbac.py::test_employee_can_edit_own_task           PASSED
tests/test_rbac.py::test_manager_can_create_project           PASSED
tests/test_rbac.py::test_admin_can_delete_task                PASSED

==================== 20 passed ====================
```

---

## RBAC Quick Reference

| Role              | Projects      | Tasks          | Finance       |
| ----------------- | ------------- | -------------- | ------------- |
| `super_admin`     | Full access   | Full access    | Create + Read |
| `project_manager` | Create + Edit | Full access    | Read only     |
| `employee`        | Read only     | Own tasks only | ❌ Blocked    |

---

## Next Step (Pending Team)

Once the team's Supabase/PostgreSQL database is ready, create `backend/.env`:

```
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SECRET_KEY=any_long_random_string
```

Then run `uvicorn app.main:app --reload` and open `http://127.0.0.1:8000/docs`
