from enum import Enum


class UserRole(str, Enum):
    super_admin = "super_admin"
    project_manager = "project_manager"
    employee = "employee"
    admin = "admin"
    manager = "manager"
    founder = "founder"
    co_founder = "co_founder"


class ProjectStatus(str, Enum):
    planning = "planning"
    active = "active"
    inactive = "inactive"
    completed = "completed"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"