import uuid

from sqlalchemy import Column, String, Boolean, Date, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.db.mixins import TimestampMixin
from app.db.enums import UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String, unique=True, index=True, nullable=False)

    password_hash = Column(String, nullable=False)

    full_name = Column(String, nullable=False)

    role = Column(Enum(UserRole), nullable=False)

    is_active = Column(Boolean, default=True)

    department = Column(String)

    designation = Column(String)

    join_date = Column(Date)

    phone = Column(String)

    address = Column(String)

    theme = Column(String)

    workspace_enabled = Column(Boolean, default=True)