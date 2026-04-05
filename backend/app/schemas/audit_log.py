from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_type: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    merchant_id: Optional[int]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    total: int
    page: int
    limit: int
    logs: list[AuditLogResponse]
