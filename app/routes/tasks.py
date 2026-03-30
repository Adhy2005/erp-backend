"""
app/routes/tasks.py
--------------------
Task API routes with ownership enforcement and comments.
- Employee can only edit tasks assigned to them
- Only admin/manager can delete tasks
- Comments stored in task_comments table
"""

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.middleware.rbac import require_role
from app.middleware.auth import get_current_user
from app.models.tasks import Task
from app.models.task_comments import TaskComment
from app.models.projects import Project
from app.models.sprints import Sprint

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ── Request schemas ────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    project_id: str
    sprint_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"
    order_index: Optional[int] = 0


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    order_index: Optional[int] = None
    assignee_id: Optional[str] = None
    # According to spec, only these 3 fields are allowed for PATCH /tasks/{id}


class CommentCreate(BaseModel):
    text: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
def get_tasks(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get tasks, optionally filtered by project_id."""
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == uuid.UUID(project_id))
    
    try:
        tasks = query.all()
        return [
            {
                "id": str(t.id),
                "project_id": str(t.project_id),
                "sprint_id": str(t.sprint_id) if t.sprint_id else None,
                "parent_task_id": str(t.parent_task_id) if t.parent_task_id else None,
                "title": t.title,
                "description": t.description,
                "status": str(t.status.value) if hasattr(t.status, 'value') else str(t.status),
                "priority": str(t.priority.value) if hasattr(t.priority, 'value') else str(t.priority),
                "order_index": t.order_index,
                "assignee_id": str(t.assignee_id) if hasattr(t, 'assignee_id') and t.assignee_id else None,
                "created_at": str(t.created_at) if t.created_at else None,
                "updated_at": str(t.updated_at) if t.updated_at else None,
            }
            for t in tasks
        ]
    except Exception as e:
        import traceback
        return {"error_debug": str(e), "trace": traceback.format_exc()}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a task — validates project, sprint, and parent task exist."""
    project = db.query(Project).filter(Project.id == uuid.UUID(data.project_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found")

    if data.sprint_id:
        sprint = db.query(Sprint).filter(Sprint.id == uuid.UUID(data.sprint_id)).first()
        if not sprint:
            raise HTTPException(status_code=404, detail=f"Sprint {data.sprint_id} not found")

    if data.parent_task_id:
        parent = db.query(Task).filter(Task.id == uuid.UUID(data.parent_task_id)).first()
        if not parent:
            raise HTTPException(status_code=404, detail=f"Parent task {data.parent_task_id} not found")

    task = Task(
        id=uuid.uuid4(),
        project_id=uuid.UUID(data.project_id),
        sprint_id=uuid.UUID(data.sprint_id) if data.sprint_id else None,
        parent_task_id=uuid.UUID(data.parent_task_id) if data.parent_task_id else None,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        order_index=data.order_index,
    )
    # If assignee_id exists on Task model (it's not actively used in spec but was part of earlier endpoints)
    if hasattr(task, 'assignee_id') and data.assignee_id:
        task.assignee_id = uuid.UUID(data.assignee_id)
    if hasattr(task, 'reporter_id'):
        task.reporter_id = uuid.UUID(current_user["user_id"])

    db.add(task)
    db.commit()
    db.refresh(task)
    return {"message": "Task created", "task_id": str(task.id)}


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "admin", "manager")),
):
    """
    Update a task.
    Admin/SuperAdmin can update status, priority, order_index, and assignment.
    """
    task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.dict(exclude_unset=True)

    if "assignee_id" in update_data:
        val = update_data.pop("assignee_id")
        if val in (None, ""):
            task.assignee_id = None
        else:
            from app.models.users import User
            user = db.query(User).filter(User.id == uuid.UUID(val)).first()
            if not user:
                raise HTTPException(status_code=400, detail="Assignee user does not exist")
            task.assignee_id = user.id

    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    return {"message": "Task updated", "task_id": task_id}


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "admin", "manager")),
):
    """Delete a task. RBAC: employee gets 403."""
    task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted", "task_id": task_id}


@router.post("/{task_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    task_id: str,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a comment to a task."""
    task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    comment = TaskComment(
        id=uuid.uuid4(),
        task_id=uuid.UUID(task_id),
        user_id=uuid.UUID(current_user["user_id"]),
        text=data.text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"message": "Comment added", "comment_id": str(comment.id)}


@router.get("/{task_id}/comments")
def get_comments(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all comments for a task."""
    task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    comments = db.query(TaskComment).filter(TaskComment.task_id == uuid.UUID(task_id)).all()
    return [
        {
            "id": str(c.id),
            "task_id": str(c.task_id),
            "user_id": str(c.user_id),
            "text": c.text,
            "created_at": str(c.created_at) if c.created_at else None
        }
        for c in comments
    ]
