from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class WxAuthStateResponse(BaseModel):
    """微信授权 URL 响应"""
    auth_url: str
    state: str
    expires_in: int  # seconds


class WxCallbackRequest(BaseModel):
    """微信回调请求（code 换 token）"""
    code: str = Field(..., description="微信授权码")
    state: str = Field(..., description="OAuth state 参数")


class WxTokenResponse(BaseModel):
    """微信登录 Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    merchant_id: int
    user_id: int
    user_role: str


class WxRefreshRequest(BaseModel):
    """刷新 Access Token"""
    refresh_token: str


class WxAccessTokenResponse(BaseModel):
    """刷新后的 Access Token"""
    access_token: str
    expires_in: int


class MerchantUserInfo(BaseModel):
    """商户用户信息（登录后返回）"""
    id: int
    merchant_id: int
    merchant_name: str
    merchant_status: str
    username: Optional[str]
    role: str
    is_active: int
