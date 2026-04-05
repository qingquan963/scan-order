from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ==================== Points Account ====================

class PointsAccountResponse(BaseModel):
    """顾客积分账户信息"""
    customer_id: int
    merchant_id: int
    points: int
    total_points: int
    visit_count: int
    last_visit: Optional[datetime] = None
    # 会员等级
    tier_name: str
    tier_threshold: int
    next_tier_name: Optional[str] = None
    next_tier_threshold: Optional[int] = None
    next_tier_points_needed: Optional[int] = None

    class Config:
        from_attributes = True


# ==================== Points History ====================

class PointsHistoryItem(BaseModel):
    """积分明细项（Phase 3B: 从 orders 表聚合）"""
    id: int
    order_id: int
    order_number: str
    change: str  # "+100" 或 "-50"
    amount: float  # 实际金额（正为得，负为扣）
    reason: str  # 消费返积分 / 积分抵扣 / 订单取消返还
    created_at: datetime


class PointsHistoryResponse(BaseModel):
    """积分明细响应"""
    current_points: int
    total_points: int
    tier_name: str
    tier_threshold: int
    next_tier_name: Optional[str] = None
    next_tier_threshold: Optional[int] = None
    next_tier_points_needed: Optional[int] = None
    items: List[PointsHistoryItem]


# ==================== Points Settings (Admin) ====================

class PointsSettingsUpdate(BaseModel):
    """积分规则配置更新"""
    points_enabled: Optional[int] = Field(None, ge=0, le=1)
    points_per_yuan: Optional[int] = Field(None, ge=1, le=10)
    points_max_discount_percent: Optional[int] = Field(None, ge=0, le=100)

    class Config:
        from_attributes = True


class PointsSettingsResponse(BaseModel):
    """积分规则配置响应"""
    points_enabled: int
    points_per_yuan: int
    points_max_discount_percent: int

    class Config:
        from_attributes = True


# ==================== Points Calculation ====================

class PointsPreview(BaseModel):
    """下单前积分预览"""
    can_use_points: bool
    max_points_usable: int
    max_discount_amount: float
    balance_points: int
