from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class WorkspaceSharedUser(Base):
    __tablename__ = "workspace_shared_users"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personal_workspace.id", ondelete="CASCADE"),
        primary_key=True
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )