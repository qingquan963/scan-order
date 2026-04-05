from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ==================== Coupon Template ====================

class CouponBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: str = Field(..., description="cash=满减券, discount=折扣券")
    threshold: Decimal = Field(default=Decimal("0"), ge=0)
    discount_value: Decimal = Field(..., gt=0)
    total_count: int = Field(..., gt=0)
    per_user_limit: int = Field(default=1, ge=1)
    valid_days: int = Field(default=30, ge=1)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CouponCreate(CouponBase):
    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ("cash", "discount"):
            raise ValueError("type must be 'cash' or 'discount'")
        return v


class CouponUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class CouponResponse(BaseModel):
    id: int
    merchant_id: int
    name: str
    type: str
    threshold: Decimal
    discount_value: Decimal
    total_count: int
    issued_count: int
    per_user_limit: int
    valid_days: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CouponListResponse(BaseModel):
    total: int
    coupons: List[CouponResponse]


# ==================== Coupon Record ====================

class CouponRecordResponse(BaseModel):
    id: int
    coupon_id: int
    coupon_name: str
    merchant_id: int
    merchant_name: str
    code: str
    status: str  # unused, used, expired
    issued_at: datetime
    used_at: Optional[datetime] = None
    expires_at: datetime
    # 折扣信息
    threshold: Decimal
    discount_value: Decimal
    coupon_type: str

    class Config:
        from_attributes = True


class MyCouponsResponse(BaseModel):
    unused: List[CouponRecordResponse]
    used: List[CouponRecordResponse]
    expired: List[CouponRecordResponse]


class AvailableCouponResponse(BaseModel):
    """可供下单使用的券（返回简化信息）"""
    id: int
    coupon_id: int
    coupon_name: str
    merchant_id: int
    merchant_name: str
    code: str
    expires_at: datetime
    threshold: Decimal
    discount_value: Decimal
    type: str  # cash, discount

    class Config:
        from_attributes = True


class CouponClaimResponse(BaseModel):
    record_id: int
    coupon_name: str
    code: str
    expires_at: datetime
    message: str = "领取成功"


class CouponRecordListResponse(BaseModel):
    total: int
    records: List[CouponRecordResponse]


# ==================== Coupon Record Detail (Admin) ====================

class CouponRecordAdminResponse(BaseModel):
    id: int
    customer_nickname: Optional[str] = None
    status: str
    issued_at: datetime
    used_at: Optional[datetime] = None
    expires_at: datetime
    code: str
    used_order_id: Optional[int] = None

    class Config:
        from_attributes = True


class CouponRecordAdminListResponse(BaseModel):
    total: int
    records: List[CouponRecordAdminResponse]
