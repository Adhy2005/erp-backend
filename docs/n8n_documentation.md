# n8n Automation Documentation
**Owner:** Adithya
**Layer:** Webhooks + Automation
**ERP Project — Week 1**
**Status:** Both workflows built and tested locally 

---

## Overview

Two n8n workflows automate external integrations into the ERP backend:

| Workflow | Trigger | Result |
|---|---|---|
| Jibble Attendance Sync | Jibble clock-in/out event | Inserts row into `attendance_logs` |
| GitHub Event Automation | GitHub PR or push event | Creates `Task` or adds `TaskComment` |

---

## Workflow 1: Jibble Attendance Sync TESTED

### Flow
```
curl / Jibble SaaS
  → n8n Webhook Trigger (POST /jibble-attendance)
    → Edit Fields node (normalize fields)
      → HTTP Request node (POST to FastAPI)
        → attendance_logs row inserted
```

### Node 1: Webhook Trigger

| Setting | Value |
|---|---|
| HTTP Method | POST |
| Path | `jibble-attendance` |
| Test URL | `http://localhost:5678/webhook-test/jibble-attendance` |
| Production URL | `http://localhost:5678/webhook/jibble-attendance` |
| Respond | Immediately |
| Authentication | None |

---

### Node 2: Edit Fields (Set)

| Field Name | Expression | Resolved Value |
|---|---|---|
| `email` | `{{ $json.body.email }}` | test@company.com |
| `clock_in` | `{{ $json.body.clock_in }}` | 2026-03-26T09:00:00 |
| `source` | `jibble` (hardcoded) | jibble |

---

### Node 3: HTTP Request

| Setting | Value |
|---|---|
| Method | POST |
| URL | `http://127.0.0.1:8000/webhooks/jibble` |
| Body Content Type | JSON |
| Specify Body | Using Fields Below |
| Send Headers | ON |
| Header: Content-Type | `application/json` |

**Body Parameters:**

| Name | Value |
|---|---|
| `email` | `{{ $json.email }}` |
| `clock_in` | `{{ $json.clock_in }}` |
| `source` | `{{ $json.source }}` |

---

### Sample Payload — curl → n8n

```powershell
curl.exe -X POST http://localhost:5678/webhook-test/jibble-attendance `
  -H "Content-Type: application/json" `
  -d '{\"email\": \"test@company.com\", \"clock_in\": \"2026-03-26T09:00:00\", \"source\": \"jibble\"}'
```

### Confirmed Response from FastAPI

```json
{
  "message": "Attendance log recorded successfully",
  "attendance_id": "b724b6e2-72da-4b28-98eb-d1ce8b0bda70"
}
```

---

## Workflow 2: GitHub Event Automation TESTED

### Flow
```
curl / GitHub
  → n8n Webhook Trigger (POST /github-events)
    → If node (check X-GitHub-Event header)
      → [pull_request] Map PR Fields → Send PR to ERP → Task created
      → [push]         Map Push Fields → Send Push to ERP → TaskComment added
```

### Node 1: Webhook Trigger

| Setting | Value |
|---|---|
| HTTP Method | POST |
| Path | `github-events` |
| Test URL | `http://localhost:5678/webhook-test/github-events` |
| Respond | Immediately |
| Authentication | None |

---

### Node 2: If (Event Router)

| Setting | Value |
|---|---|
| Condition | `{{ $json.headers["x-github-event"] === "pull_request" }}` |
| True branch | → Map PR Fields |
| False branch | → Map Push Fields |

---

### Node 3a: Map PR Fields (Edit Fields)

| Field | Expression |
|---|---|
| `action` | `{{ $json.body.action }}` |
| `repository_name` | `{{ $json.body.repository.name }}` |
| `pr_title` | `{{ $json.body.pull_request.title }}` |
| `pr_body` | `{{ $json.body.pull_request.body }}` |
| `pr_number` | `{{ $json.body.pull_request.number }}` |
| `event_type` | `pull_request` (hardcoded) |

### Node 4a: Send PR to ERP (HTTP Request)

| Setting | Value |
|---|---|
| Method | POST |
| URL | `http://127.0.0.1:8000/webhooks/github` |
| Header: X-GitHub-Event | `pull_request` |
| Body: action | `{{ $json.action }}` |
| Body: repository | `{{ { "name": $json.repository_name } }}` |
| Body: pull_request | `{{ { "title": $json.pr_title, "body": $json.pr_body, "number": $json.pr_number } }}` |

---

### Node 3b: Map Push Fields (Edit Fields)

| Field | Expression |
|---|---|
| `repository_name` | `{{ $json.body.repository.name }}` |
| `commit_message` | `{{ $json.body.commits[$json.body.commits.length - 1].message }}` |
| `ref` | `{{ $json.body.ref }}` |
| `event_type` | `push` (hardcoded) |

### Node 4b: Send Push to ERP (HTTP Request)

| Setting | Value |
|---|---|
| Method | POST |
| URL | `http://127.0.0.1:8000/webhooks/github` |
| Header: X-GitHub-Event | `push` |
| Body: repository | `{{ { "name": $json.repository_name } }}` |
| Body: commits | `{{ [{ "message": $json.commit_message }] }}` |
| Body: ref | `{{ $json.ref }}` |

---

### Sample Payload — PR event

```powershell
curl.exe -X POST http://localhost:5678/webhook-test/github-events `
  -H "Content-Type: application/json" `
  -H "x-github-event: pull_request" `
  -d '{\"action\": \"opened\", \"pull_request\": {\"title\": \"Fix login\", \"body\": \"bug fix\", \"number\": 1}, \"repository\": {\"name\": \"erp-backend\"}}'
```

### Sample Payload — Push event

```powershell
curl.exe -X POST http://localhost:5678/webhook-test/github-events `
  -H "Content-Type: application/json" `
  -H "x-github-event: push" `
  -d '{\"commits\": [{\"message\": \"fix null pointer\"}], \"repository\": {\"name\": \"erp-backend\"}, \"ref\": \"refs/heads/main\"}'
```

---

## Option A vs Option B — Justification

Both options are implemented in the same endpoint. The `X-GitHub-Event` header determines which path runs:

**PR opened → Create Task (Option A)**
A pull request represents a discrete unit of new work. Creating a task keeps the ERP synchronized with development activity automatically. Tasks are the correct record for tracking work items.

**Push → Add Comment (Option B)**
A push represents ongoing activity on existing work. A `TaskComment` is the right record — it attaches commit context to an existing task without creating duplicate task entries.

---

## Pre-requisites for This Workflow to Work

The following must exist in the DB before the GitHub workflow runs:

```sql
-- A project whose name matches the GitHub repository name exactly
INSERT INTO projects (id, name, description, manager_id, status, start_date, created_at, updated_at)
VALUES (gen_random_uuid(), 'erp-backend', 'ERP Backend Project',
        (SELECT id FROM users WHERE email = 'test@company.com'),
        'active', CURRENT_DATE, NOW(), NOW());

-- For push events: at least one task must exist in that project
-- (auto-created when a PR event runs first)
```

---

## Environment Variables Required

```env
# .env file
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/erp_db_local
```

n8n does not need environment variables for local testing — URLs are hardcoded to `127.0.0.1:8000`.