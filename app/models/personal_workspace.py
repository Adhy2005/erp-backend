import uuid

from sqlalchemy import Column, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class PersonalWorkspace(Base):
    __tablename__ = "personal_workspace"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personal_workspace.id")
    )

    is_shared = Column(Boolean)