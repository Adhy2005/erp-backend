# Governance Checklist — Webhooks Layer
**Owner:** Adithya
**Layer:** Webhooks + Automation
**Status:** All rules verified and passing
**Date:** Week 1

---

## Rule-by-Rule Verification

| Rule | Status | Evidence |
|---|---|---|
| No direct SQL in routes | PASS | `router.py` only calls service functions. All DB queries via SQLAlchemy ORM inside `service.py` |
| No hardcoded credentials | PASS | All secrets loaded via `os.getenv()` from `.env`. No literal passwords or tokens in code |
| Business logic in service, not route | PASS | `router.py` is thin — parses request, calls service, returns response. Zero logic inside routes |
| Dependency injection for DB | PASS | `Depends(get_db)` used in every route. No manual session creation inside routes |
| FK validation — user must exist | PASS | Jibble service queries `User` by email before inserting `AttendanceLog`. Returns 404 if not found |
| Inactive user blocked | PASS | `is_active == True` filter applied in user lookup query |
| FK validation — project must exist | PASS | GitHub service queries `Project` by name before creating Task or TaskComment. Returns 404 if not found |
| FK validation — task must exist | PASS | GitHub push handler queries most recent Task in project before inserting TaskComment |
| Tests: success + failure + FK cases | PASS | Jibble: 6 tests. GitHub: 8 tests. All 14 passing |
| Schema alignment | PASS | Uses Alen's models: `User`, `AttendanceLog`, `Task`, `TaskComment`, `Project`. No redefinitions |
| Role enforcement correct | PASS | Webhooks are external callers — JWT not applicable here. RBAC belongs to Leelavathi's layer |
| No circular dependencies | PASS | Webhook layer imports only from `app.models.*` and `app.db.session` |

---

## File-by-File Breakdown

### `webhooks/jibble/router.py`
- Thin route: `POST /webhooks/jibble`
- Accepts `JibblePayload`, calls `process_jibble_event()`
- Uses `Depends(get_db)` for DB session injection
- Returns `JibbleResponse` with `message` and `attendance_id`

### `webhooks/jibble/service.py`
- Looks up `User` by `email` with `is_active == True`
- Raises `HTTP 404` if user not found
- Inserts `AttendanceLog` via ORM with `clock_in`, `clock_out`, `source`
- No raw SQL anywhere

### `webhooks/jibble/schemas.py`
- `JibblePayload`: `email` (EmailStr), `clock_in` (datetime), `clock_out` (optional), `source` (default: jibble)
- Validators: `clock_out` must be after `clock_in`, `source` cannot be blank
- `JibbleResponse`: `message`, `attendance_id`

### `webhooks/github/router.py`
- Thin route: `POST /webhooks/github`
- Reads `X-GitHub-Event` header to determine event type
- Calls `process_github_event()` from service
- No business logic in route

### `webhooks/github/service.py`
- `pull_request` + `action=opened` → creates `Task` linked to matched project
- `push` → adds `TaskComment` on most recent task in matched project
- Both handlers validate project exists by `Project.name == repository.name`
- Push handler also validates a task exists before commenting
- Unsupported event type → `HTTP 400`

### `webhooks/github/schemas.py`
- `GitHubPayload`: supports both PR and push event structures
- `PullRequest`: `title`, `body`, `number`
- `Repository`: `name`
- `Commit`: `message`

---

## Test Coverage Summary

### Jibble — 6/6 PASSED

| Test | Type |
|---|---|
| `test_jibble_clock_in_success` | Success |
| `test_jibble_clock_in_only` | Success variant |
| `test_jibble_user_not_found` | FK Violation |
| `test_jibble_invalid_payload_missing_clock_in` | Failure |
| `test_jibble_clock_out_before_clock_in` | Business rule |
| `test_jibble_inactive_user_blocked` | Unauthorized |

### GitHub — 8/8 PASSED

| Test | Type |
|---|---|
| `test_pr_opened_creates_task` | Success |
| `test_pr_no_matching_project` | FK Violation |
| `test_pr_missing_pull_request_field` | Failure |
| `test_push_adds_comment` | Success |
| `test_push_no_commits` | Failure |
| `test_push_no_tasks_in_project` | FK Violation |
| `test_missing_github_event_header` | Unauthorized |
| `test_unsupported_event_type` | Failure |

---

## n8n Integration — Live Tested 

### Jibble Workflow
- Tested end to end with real curl payload
- Response received: `"Attendance log recorded successfully"` with UUID `b724b6e2-72da-4b28-98eb-d1ce8b0bda70`
- All 3 nodes showed green in n8n execution

### GitHub Workflow
- PR event tested: task created in DB
- Push event tested: comment added to most recent task
- Both If node branches verified working

---

## Hard Rules Compliance

| Rule | Status |
|---|---|
| No one modifies another intern's layer | Only touched `webhooks/`, `tests/webhooks/`, `docs/` |
| No schema changes without migration | No schema changes made |
| No merging if tests fail | All 14 tests passing before PR |
| No skipping Alembic | No manual table creation |
| No circular dependencies | Verified |
| No direct DB logic inside route files | All DB logic in `service.py` |