import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    name = Column(String, nullable=False)

    url = Column(String, nullable=False)

    uploaded_at = Column(DateTime)