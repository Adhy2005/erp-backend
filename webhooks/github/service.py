"""
Event-driven routing:
  - pull_request (action=opened) → Option A: CREATE a task
  - push with commits            → Option B: ADD a comment to task_comments
 
Justification (for PR):
  A single webhook handles both GitHub event types cleanly.
  PR events signal new work → task creation is appropriate.
  Push events signal code activity on existing work → commenting is appropriate.
  This avoids maintaining two separate endpoints for the same GitHub source.
"""
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
 
from app.models.tasks import Task
from app.models.task_comments import TaskComment
from app.models.projects import Project
from webhooks.github.schemas import GitHubPayload
 
 
# ── Option A: Create a Task from a Pull Request event ─────────────────────────
def handle_pull_request_opened(payload: GitHubPayload, db: Session) -> Task:
    """
    When a PR is opened on GitHub:
    - Extract PR title and body
    - Find the first available project (or raise 404)
    - Insert a new task linked to that project
    """
    pr = payload.pull_request
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pull_request field missing in payload",
        )
 
    # Find a project to link the task to (uses repo name to match)
    project = (
        db.query(Project)
        .filter(Project.name == payload.repository.name)
        .first()
    )
 
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No project found matching repository: {payload.repository.name}",
        )
 
    task = Task(
        id=uuid.uuid4(),
        title=pr.title,
        description=pr.body or f"Auto-created from GitHub PR #{pr.number}",
        project_id=project.id,
        status="todo",
        priority="medium",
        order_index=0,
    )
 
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
 
 
# ── Option B: Add a Comment from a Push event ─────────────────────────────────
def handle_push_event(payload: GitHubPayload, db: Session) -> TaskComment:
    """
    When a push is made to GitHub:
    - Extract the latest commit message
    - Find the most recent task in the matched project
    - Insert a task_comment with the commit message
    """
    commits = payload.commits
    if not commits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No commits found in push payload",
        )
 
    commit_message = commits[-1].message  # use the latest commit
 
    # Find project by repo name
    project = (
        db.query(Project)
        .filter(Project.name == payload.repository.name)
        .first()
    )
 
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No project found matching repository: {payload.repository.name}",
        )
 
    # Find most recent task in that project
    task = (
        db.query(Task)
        .filter(Task.project_id == project.id)
        .order_by(Task.id.desc())
        .first()
    )
 
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tasks found in project to comment on",
        )
 
    comment = TaskComment(
        id=uuid.uuid4(),
        task_id=task.id,
        text=f"[GitHub Push] {commit_message}",
    )
 
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
 
 
# ── Event Router ──────────────────────────────────────────────────────────────
def process_github_event(
    payload: GitHubPayload,
    event_type: str,
    db: Session,
) -> dict:
    """
    Routes GitHub webhook events to the correct handler:
      - X-GitHub-Event: pull_request + action=opened → create task
      - X-GitHub-Event: push                         → add comment
    """
    if event_type == "pull_request" and payload.action == "opened":
        task = handle_pull_request_opened(payload, db)
        return {
            "message": "Task created from GitHub PR",
            "event_type": "task_created",
            "record_id": str(task.id),
        }
 
    elif event_type == "push":
        comment = handle_push_event(payload, db)
        return {
            "message": "Comment added from GitHub push",
            "event_type": "comment_added",
            "record_id": str(comment.id),
        }
 
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported GitHub event type: {event_type}",
        )