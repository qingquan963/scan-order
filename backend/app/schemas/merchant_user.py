from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class MerchantUserBase(BaseModel):
    username: Optional[str] = Field(None, max_length=50)


class MerchantUserCreate(MerchantUserBase):
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    merchant_id: int
    role: str = Field(default="owner", max_length=20)


class MerchantUserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    role: Optional[str] = Field(None, max_length=20)
    is_active: Optional[int] = None


class MerchantUserResponse(BaseModel):
    id: int
    merchant_id: int
    username: Optional[str]
    wx_openid: Optional[str]
    role: str
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MerchantUserLogin(BaseModel):
    """商户用户用户名密码登录"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)
