"""
认证相关 Pydantic Schema（Phase 2）
"""

from pydantic import BaseModel
from typing import Optional


class TenantInfo(BaseModel):
    """租户信息响应"""
    id: str
    name: str
    slug: str
    tier: str
    subscription_status: str
    subscription_expires_at: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
