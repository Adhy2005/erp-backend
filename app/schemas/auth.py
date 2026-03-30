"""
app/schemas/auth.py
-------------------
Pydantic request/response models for auth endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "alice@example.com",
                "password": "secret123",
                "full_name": "Alice Smith",
                "role": "employee",
            }
        }
    )

    email: EmailStr
    password: str = Field(..., min_length=6, description="Minimum 6 characters")
    full_name: str = Field(..., min_length=1)
    role: str = Field(default="employee", description="employee | project_manager | super_admin")


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "alice@example.com",
                "password": "secret123",
            }
        }
    )

    email: EmailStr
    password: str


class OAuthRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "alice@example.com",
                "full_name": "Alice Smith",
                "provider": "jibble",
            }
        }
    )

    email: EmailStr
    full_name: Optional[str] = "OAuth User"
    provider: Optional[str] = "jibble"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
