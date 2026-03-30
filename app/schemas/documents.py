"""
app/schemas/documents.py
------------------------
Pydantic request/response models for user document endpoints.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class DocumentCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Resume.pdf",
                "url": "https://storage.example.com/docs/resume.pdf",
            }
        }
    )

    name: str
    url: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    url: str
    uploaded_at: Optional[datetime] = None
