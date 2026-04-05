from pydantic import BaseModel, Field
from typing import Optional


class Token(BaseModel):
    """商户登录 Token 响应（向后兼容 Phase 1/2）"""
    access_token: str
    token_type: str = "bearer"
    merchant_id: int


class TokenData(BaseModel):
    """Token数据模型"""
    merchant_id: Optional[int] = None
    user_id: Optional[int] = None
    user_type: Optional[str] = None


class LoginRequest(BaseModel):
    """商户登录请求模型"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RegisterRequest(BaseModel):
    """商户注册请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UnifiedTokenResponse(BaseModel):
    """统一认证 Token 响应（Phase 3A - 支持 Cookie）"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    merchant_id: int
    user_id: int
    user_role: str
    merchant_status: str


class MerchantUserTokenResponse(BaseModel):
    """商户用户登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    merchant_id: int
    merchant_name: str
    merchant_status: str
    user_id: int
    username: Optional[str]
    role: str
