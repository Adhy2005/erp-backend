import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.db.mixins import TimestampMixin


class Sprint(Base, TimestampMixin):
    __tablename__ = "sprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )

    name = Column(String)

    goal = Column(String, nullable=True)

    is_active = Column(Boolean, default=False)