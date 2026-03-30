import uuid

from sqlalchemy import Column, Float, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.db.mixins import TimestampMixin


class FinanceEntry(Base, TimestampMixin):
    __tablename__ = "finance_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=True
    )

    amount = Column(Float)

    type = Column(String)
    client_name = Column(String)
    currency = Column(String, default="INR")
    category = Column(String, nullable=True)

    description = Column(String)