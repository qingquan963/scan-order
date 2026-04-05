from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# 订单项基础Schema
class OrderItemBase(BaseModel):
    dish_id: int
    dish_name: str
    unit_price: float
    quantity: int = Field(ge=1, default=1)
    subtotal: float
    note: Optional[str] = None


# 订单项创建Schema
class OrderItemCreate(OrderItemBase):
    pass


# 订单项响应Schema
class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# 订单基础Schema
class OrderBase(BaseModel):
    table_id: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    remark: Optional[str] = None


# 订单创建Schema
class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


# 订单更新Schema
class OrderUpdate(BaseModel):
    status: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    remark: Optional[str] = None


# 订单状态更新Schema
class OrderStatusUpdate(BaseModel):
    status: str


# 订单响应Schema
class OrderResponse(OrderBase):
    id: int
    merchant_id: int
    order_number: str
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    # Phase 2 新增字段
    payment_token: Optional[str] = None
    paid_at: Optional[datetime] = None
    payment_mode: Optional[str] = None  # 商户支付模式
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


# 订单列表响应Schema
class OrderListResponse(BaseModel):
    total: int
    page: int
    limit: int
    orders: List[OrderResponse]


# 统计相关Schema
class TodayStatsResponse(BaseModel):
    total_orders: int
    total_revenue: float
    completed_orders: int
    pending_orders: int
    cancelled_orders: int


class SalesStatsResponse(BaseModel):
    period: str
    total_revenue: float
    total_orders: int
    average_order_value: float
    data: List[dict]  # 具体数据点，如按天/周/月统计