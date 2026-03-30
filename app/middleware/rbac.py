"""
app/middleware/rbac.py
----------------------
Role enforcement — same logic regardless of database type.
require_role() blocks requests from wrong roles with 403 Forbidden,
before any database query runs.
"""

from fastapi import Depends, HTTPException, status
from app.middleware.auth import get_current_user


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory.
    Place on any route to restrict access by role.

    Example:
        @router.delete("/tasks/{id}")
        async def delete_task(user = Depends(require_role("super_admin", "project_manager"))):
            ...
    """
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Your role '{current_user['role']}' is not permitted. "
                    f"Required: {list(allowed_roles)}"
                ),
            )
        return current_user
    return role_checker
