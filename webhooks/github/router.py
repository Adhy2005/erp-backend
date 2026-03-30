from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session
from typing import Annotated
 
from app.db.session import get_db
from webhooks.github.schemas import GitHubPayload, GitHubWebhookResponse
from webhooks.github.service import process_github_event
 
router = APIRouter(prefix="/webhooks", tags=["Webhooks - GitHub"])
 
 
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
 
    return GitHubWebhookResponse(**result)