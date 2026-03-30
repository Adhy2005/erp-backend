# app/webhooks/github/schemas.py
from pydantic import BaseModel
from typing import Optional
 
 
class GitHubCommit(BaseModel):
    message: str
 
 
class GitHubRepository(BaseModel):
    name: str
 
 
class GitHubPullRequest(BaseModel):
    title: str
    body: Optional[str] = None
    number: int
 
 
class GitHubPayload(BaseModel):
    """
    Validates incoming GitHub webhook payload.
    Supports two event types:
      - pull_request (action=opened) → creates a Task
      - push (with commits)          → adds a comment to task_comments
    """
    action: Optional[str] = None          # "opened" for PR events
    ref: Optional[str] = None             # "refs/heads/feature/xyz" for push
    repository: GitHubRepository
    commits: Optional[list[GitHubCommit]] = None
    pull_request: Optional[GitHubPullRequest] = None
 
 
class GitHubWebhookResponse(BaseModel):
    message: str
    event_type: str                        # "task_created" or "comment_added"
    record_id: str