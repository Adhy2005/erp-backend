import uuid

from sqlalchemy import Column, DateTime, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    clock_in = Column(DateTime(timezone=True))

    clock_out = Column(DateTime(timezone=True))

    source = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())