from sqlalchemy.orm import Session
from fastapi import HTTPException, status
 
from app.models.users import User         # Alen's schema layer
from app.models.attendance_logs import AttendanceLog
from webhooks.jibble.schemas import JibblePayload
 
 
def process_jibble_event(payload: JibblePayload, db: Session) -> AttendanceLog:
    """
    Core logic for the Jibble webhook:
      1. Lookup user by email (must exist)
      2. Insert attendance_log row
      3. Return the created record
    No direct SQL. No hardcoded credentials. Uses ORM only.
    """
 
    # --- 1. Resolve user ---
    user: User | None = (
        db.query(User)
        .filter(User.email == payload.email, User.is_active == True)
        .first()
    )
 
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active user found with email: {payload.email}",
        )
 
    # --- 2. Insert attendance log ---
    log = AttendanceLog(
        user_id=user.id,
        clock_in=payload.clock_in,
        clock_out=payload.clock_out,
        source=payload.source,
    )
 
    db.add(log)
    db.commit()
    db.refresh(log)
 
    return log