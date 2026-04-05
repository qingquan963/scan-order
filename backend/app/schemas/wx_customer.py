from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== Customer Auth (WeChat Mini-Program) ====================

class WxCustomerLoginRequest(BaseModel):
    """顾客微信登录请求（code 换 openid）"""
    code: str = Field(..., description="微信授权码")
    merchant_id: int = Field(..., description="要绑定的商户ID")


class WxCustomerTokenResponse(BaseModel):
    """顾客登录成功返回"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 7200  # 2小时
    customer_id: int
    binding_id: int
    merchant_id: int
    merchant_name: str
    points: int = 0
    tier_name: str = "普通会员"


# ==================== Customer Info ====================

class CustomerMeResponse(BaseModel):
    """顾客个人信息（含积分和等级）"""
    customer_id: int
    wx_nickname: Optional[str] = None
    wx_avatar: Optional[str] = None
    binding_id: int
    merchant_id: int
    merchant_name: str
    points: int
    total_points: int
    visit_count: int
    last_visit: Optional[datetime] = None
    tier_name: str
    tier_threshold: int
    next_tier_name: Optional[str] = None
    next_tier_threshold: Optional[int] = None
    next_tier_points_needed: Optional[int] = None
    points_enabled: bool
    points_per_yuan: int
    points_max_discount_percent: int

    class Config:
        from_attributes = True


# ==================== Customer Order ====================

class CustomerOrderItemCreate(BaseModel):
    dish_id: int
    quantity: int = Field(ge=1, default=1)
    note: Optional[str] = None


class CustomerOrderCreate(BaseModel):
    """顾客下单（支持优惠券和积分抵扣）"""
    table_id: int
    items: List[CustomerOrderItemCreate]
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    remark: Optional[str] = None
    coupon_record_id: Optional[int] = None  # 要核销的优惠券记录ID
    use_points: Optional[int] = Field(default=0, ge=0)  # 要使用的积分数量
