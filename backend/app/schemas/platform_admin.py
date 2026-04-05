from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class PlatformAdminBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)


class PlatformAdminCreate(PlatformAdminBase):
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(default="admin", max_length=20)


class PlatformAdminUpdate(BaseModel):
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    is_active: Optional[int] = None
    role: Optional[str] = Field(None, max_length=20)


class PlatformAdminResponse(PlatformAdminBase):
    id: int
    role: str
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
