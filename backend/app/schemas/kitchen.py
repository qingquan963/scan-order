"""
Phase Kitchen - 后厨屏 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── PIN 验证 ────────────────────────────────────────────────

class KitchenAuthRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=4, description="4位PIN码")


class KitchenAuthResponse(BaseModel):
    token: str = Field(..., description="后厨访问令牌")
    expires_in: int = Field(..., description="有效期（秒）")


# ─── 订单项 ──────────────────────────────────────────────────

class KitchenItemResponse(BaseModel):
    id: int
    dish_name: str
    quantity: int
    note: Optional[str] = None
    is_done: bool = False

    class Config:
        from_attributes = True


# ─── 订单 ─────────────────────────────────────────────────────

class KitchenOrderResponse(BaseModel):
    id: int
    order_number: str
    table_number: str
    kitchen_status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    remark: Optional[str] = None
    items: List[KitchenItemResponse] = []

    class Config:
        from_attributes = True


class KitchenOrderListResponse(BaseModel):
    orders: List[KitchenOrderResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ─── 接单响应 ────────────────────────────────────────────────

class KitchenAcceptResponse(BaseModel):
    id: int
    kitchen_status: str
    updated_at: datetime
    message: str = "已接单"


# ─── 标记完成响应 ────────────────────────────────────────────

class KitchenItemDoneResponse(BaseModel):
    item_id: int
    is_done: bool
    order_id: int
    order_all_done: bool
    updated_at: datetime


# ─── 错误响应 ────────────────────────────────────────────────

class KitchenConflictResponse(BaseModel):
    error: str = "conflict"
    message: str
    current_kitchen_status: Optional[str] = None


class KitchenErrorResponse(BaseModel):
    error: str
    message: str
