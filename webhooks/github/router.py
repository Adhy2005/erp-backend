from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session
from typing import Annotated
import datetime

from app.db.session import get_db
from webhooks.github.schemas import GitHubPayload, GitHubWebhookResponse
from webhooks.github.service import process_github_event

# ── In-Memory Log for UI ──────────────────────────────────────────────────────
github_events_log = []

router = APIRouter(prefix="/webhooks", tags=["Webhooks - GitHub"])
api_webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks UI"])

@api_webhooks_router.get("/")
def get_recent_webhooks():
    """Returns the most recent GitHub webhook events for the UI."""
    return github_events_log

@router.post(
    "/github",
    response_model=GitHubWebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive GitHub push and pull_request events",
)
def github_webhook(
    payload: GitHubPayload,
    db: Session = Depends(get_db),
    x_github_event: Annotated[str | None, Header()] = None,
):
    """
    Webhook endpoint called by GitHub.
    Routes based on X-GitHub-Event header:
      - pull_request (action=opened) → creates a Task
      - push                         → adds a comment to task_comments
    """
    if not x_github_event:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="X-GitHub-Event header is required",
        )

    result = process_github_event(
        payload=payload,
        event_type=x_github_event,
        db=db,
    )

    # Track event in memory for UI feed
    if x_github_event in ("pull_request", "push"):
        event_data = {
            "id": len(github_events_log) + 1,
            "event_type": x_github_event,
            "action": payload.action or "pushed",
            "repository_name": payload.repository.name if payload.repository else "Unknown",
            "pr_title": payload.pull_request.title if payload.pull_request else (payload.commits[-1].message if payload.commits else None),
            "pr_number": payload.pull_request.number if payload.pull_request else None,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
        github_events_log.insert(0, event_data)
        if len(github_events_log) > 50:
            github_events_log.pop()

    return GitHubWebhookResponse(**result)