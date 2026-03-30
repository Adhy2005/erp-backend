from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
 
from  app.db.session import get_db                            # Alen's DB session
from webhooks.jibble.schemas import JibblePayload, JibbleResponse
from webhooks.jibble.service import process_jibble_event
 
router = APIRouter(prefix="/webhooks", tags=["Webhooks - Jibble"])
 
 
@router.post(
    "/jibble",
    response_model=JibbleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive Jibble clock-in/clock-out events",
)
def jibble_webhook(
    payload: JibblePayload,
    db: Session = Depends(get_db),           # dependency injection — no direct DB logic here
):
    """
    Webhook endpoint called by Jibble (or n8n relaying Jibble events).
    Validates payload shape, looks up the user, and inserts an attendance_log.
    """
    log = process_jibble_event(payload=payload, db=db)
 
    return JibbleResponse(
        message="Attendance log recorded successfully",
        attendance_id=str(log.id),
    )