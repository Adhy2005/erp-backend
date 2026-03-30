"""
app/routes/attendance.py
------------------------
Attendance REST API endpoints (separate from the Jibble webhook).
Reuses the existing AttendanceLog model.

  POST /attendance/clock-in      — Manual clock-in for current user
  POST /attendance/clock-out     — Manual clock-out for current user
  GET  /attendance/today         — Today's status for current user
  GET  /attendance/my            — Current user's attendance history
  GET  /attendance/team          — All employees' attendance (admin/PM only)
"""

import uuid
from datetime import datetime, date, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date, desc

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_role
from app.models.attendance_logs import AttendanceLog
from app.models.users import User

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ── Helper ─────────────────────────────────────────────────────────────────────

def _format_log(log: AttendanceLog, user_name: str = None) -> dict:
    total_hours = None
    if log.clock_in and log.clock_out:
        delta = log.clock_out - log.clock_in
        total_hours = round(delta.total_seconds() / 3600, 2)

    return {
        "id": str(log.id),
        "user_id": str(log.user_id),
        "user_name": user_name,
        "clock_in": log.clock_in.isoformat() if log.clock_in else None,
        "clock_out": log.clock_out.isoformat() if log.clock_out else None,
        "total_hours": total_hours,
        "source": log.source,
        "date": log.clock_in.astimezone(timezone.utc).date().isoformat() if log.clock_in else None,
    }


# ── POST /attendance/clock-in ─────────────────────────────────────────────────

@router.post("/clock-in", status_code=status.HTTP_201_CREATED)
def clock_in(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Clock in the current user. 
    User can check-in ONLY if there is no active session (check_out is NULL).
    """
    user_id = uuid.UUID(current_user["user_id"])
    now = datetime.now(timezone.utc)

    # Check for *any* existing open session
    existing = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.user_id == user_id,
            AttendanceLog.clock_out == None,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already checked in. Please check out first.",
        )

    log = AttendanceLog(
        id=uuid.uuid4(),
        user_id=user_id,
        clock_in=now,
        source="manual",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return _format_log(log, user_name=current_user.get("sub"))


# ── POST /attendance/clock-out ────────────────────────────────────────────────

@router.post("/clock-out")
def clock_out(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Clock out the current user. Finds the latest active session and sets clock_out.
    """
    user_id = uuid.UUID(current_user["user_id"])
    now = datetime.now(timezone.utc)

    # Find the latest active session (no clock_out yet)
    log = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.user_id == user_id,
            AttendanceLog.clock_out == None,
        )
        .order_by(desc(AttendanceLog.clock_in))
        .first()
    )

    if not log:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active check-in session found. Please check in first.",
        )

    log.clock_out = now
    db.commit()
    db.refresh(log)

    return _format_log(log, user_name=current_user.get("sub"))


# ── GET /attendance/today ─────────────────────────────────────────────────────

@router.get("/today")
def get_today_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get current attendance status for the user.
    Returns whether they are checked in, the current session, and the last session.
    """
    user_id = uuid.UUID(current_user["user_id"])
    
    # 1. Check for active session
    active_session = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.user_id == user_id,
            AttendanceLog.clock_out == None,
        )
        .first()
    )

    # 2. Get last completed session (today only? the user said multiple per day, 
    # so we'll show the last completed one)
    last_session = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.user_id == user_id,
            AttendanceLog.clock_out != None,
        )
        .order_by(desc(AttendanceLog.clock_in))
        .first()
    )

    return {
        "is_checked_in": active_session is not None,
        "current_session": _format_log(active_session) if active_session else None,
        "last_session": _format_log(last_session) if last_session else None,
    }


# ── GET /attendance/my ────────────────────────────────────────────────────────

@router.get("/my")
def get_my_attendance(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the current user's attendance history (last 30 days)."""
    user_id = uuid.UUID(current_user["user_id"])
    since = datetime.utcnow() - timedelta(days=30)

    logs = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.user_id == user_id,
            AttendanceLog.clock_in >= since,
        )
        .order_by(AttendanceLog.clock_in.desc())
        .all()
    )

    return [_format_log(log, user_name=current_user.get("sub")) for log in logs]


# ── GET /attendance/team ──────────────────────────────────────────────────────

@router.get("/team")
def get_team_attendance(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("super_admin", "project_manager", "manager", "admin", "founder", "co_founder")),
):
    """
    Get all employees' attendance for the last 30 days.
    RBAC: Only super_admin and project_manager.
    """
    since = datetime.utcnow() - timedelta(days=30)

    logs = (
        db.query(AttendanceLog, User.full_name)
        .join(User, AttendanceLog.user_id == User.id)
        .filter(AttendanceLog.clock_in >= since)
        .order_by(AttendanceLog.clock_in.desc())
        .all()
    )

    return [_format_log(log, user_name=name) for log, name in logs]
