from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
 
 
class JibblePayload(BaseModel):
    """
    Validates the incoming Jibble webhook payload.
    Jibble sends employee clock-in/clock-out events.
    """
    email: EmailStr
    clock_in: datetime
    clock_out: Optional[datetime] = None
    source: str = "jibble"
 
    @field_validator("source")
    @classmethod
    def source_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source cannot be blank")
        return v.strip()
 
    @field_validator("clock_out")
    @classmethod
    def clock_out_after_clock_in(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None and "clock_in" in info.data:
            if v <= info.data["clock_in"]:
                raise ValueError("clock_out must be after clock_in")
        return v
 
 
class JibbleResponse(BaseModel):
    message: str
    attendance_id: str