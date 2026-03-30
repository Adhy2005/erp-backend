"""
app/schemas/users.py
--------------------
Pydantic request/response models for user profile endpoints.
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    department: Optional[str] = None
    designation: Optional[str] = None
    join_date: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    theme: Optional[str] = None
    workspace_enabled: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "department": "Engineering",
                "designation": "Senior Developer",
                "phone": "+91-9876543210",
                "address": "123 Main Street, Bangalore",
            }
        }
    )

    department: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class PreferencesUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "theme": "dark",
                "workspace_enabled": True,
            }
        }
    )

    theme: Optional[str] = None
    workspace_enabled: Optional[bool] = None
