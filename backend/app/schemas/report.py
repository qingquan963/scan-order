from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ─── 营收日报 ────────────────────────────────────────────────

class DailyRevenueItem(BaseModel):
    stat_date: date
    total_orders: int = 0
    total_amount: Decimal = Decimal("0")
    avg_order_amount: Decimal = Decimal("0")
    paid_count: int = 0
    cancelled_count: int = 0
    cash_orders: int = 0
    credit_orders: int = 0
    coupon_discount: Decimal = Decimal("0")
    points_discount: Decimal = Decimal("0")
    new_customers: int = 0
    returning_customers: int = 0
    is_finalized: int = 0

    class Config:
        from_attributes = True


class DailyRevenueSummary(BaseModel):
    total_orders: int = 0
    total_amount: Decimal = Decimal("0")
    avg_order_amount: Decimal = Decimal("0")


class DailyRevenuePagination(BaseModel):
    page: int = 1
    page_size: int = 31
    total: int = 0


class DailyRevenueResponse(BaseModel):
    items: List[DailyRevenueItem]
    summary: DailyRevenueSummary
    pagination: DailyRevenuePagination


# ─── 营收月报 ────────────────────────────────────────────────

class MonthlyRevenueItem(BaseModel):
    stat_year: int
    stat_month: int
    total_orders: int = 0
    total_amount: Decimal = Decimal("0")
    avg_order_amount: Decimal = Decimal("0")
    paid_count: int = 0
    cancelled_count: int = 0
    cash_orders: int = 0
    credit_orders: int = 0
    coupon_discount: Decimal = Decimal("0")
    points_discount: Decimal = Decimal("0")
    new_customers: int = 0
    returning_customers: int = 0
    is_finalized: int = 0

    class Config:
        from_attributes = True


class MonthlyRevenueSummary(BaseModel):
    total_orders: int = 0
    total_amount: Decimal = Decimal("0")
    avg_order_amount: Decimal = Decimal("0")


class MonthlyRevenueResponse(BaseModel):
    items: List[MonthlyRevenueItem]
    summary: MonthlyRevenueSummary


# ─── 菜品销量 ────────────────────────────────────────────────

class DishRankingItem(BaseModel):
    dish_id: int
    dish_name: str
    category_name: Optional[str] = None
    total_quantity: int = 0
    total_amount: Decimal = Decimal("0")
    order_count: int = 0
    avg_price: Decimal = Decimal("0")

    class Config:
        from_attributes = True


class DishRankingSummary(BaseModel):
    total_dish_types: int = 0
    total_dish_quantity: int = 0


class DishRankingResponse(BaseModel):
    items: List[DishRankingItem]
    summary: DishRankingSummary


# ─── 顾客分析 ────────────────────────────────────────────────

class CustomerItem(BaseModel):
    customer_key: str  # 内部用 customer_name 作为唯一标识
    nickname: str
    avatar_url: Optional[str] = None
    visit_count: int = 0
    total_orders: int = 0
    total_amount: Decimal = Decimal("0")
    avg_order_amount: Decimal = Decimal("0")
    last_visit: Optional[datetime] = None
    tier_name: str = "普通会员"
    total_points: int = 0
    new_customer: bool = False

    class Config:
        from_attributes = True


class CustomerSummary(BaseModel):
    avg_total_per_customer: Decimal = Decimal("0")
    avg_orders_per_customer: Decimal = Decimal("0")


class CustomerResponse(BaseModel):
    items: List[CustomerItem]
    total: int = 0
    summary: CustomerSummary


# ─── 顾客群体画像 ────────────────────────────────────────────

class TierDistribution(BaseModel):
    tier: str
    count: int = 0
    percentage: float = 0.0


class CustomerSegmentsResponse(BaseModel):
    total_customers: int = 0
    new_today: int = 0
    new_this_month: int = 0
    active_this_month: int = 0
    inactive_30d: int = 0
    tier_distribution: List[TierDistribution] = []
    avg_points_per_customer: Decimal = Decimal("0")
    avg_visit_per_customer: float = 0.0


# ─── 报表修正 ────────────────────────────────────────────────

class RegenerateRequest(BaseModel):
    report_type: str = Field(..., pattern="^(daily|monthly)$")
    start_date: date
    end_date: date
    reason: Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def end_not_in_future(cls, v: date) -> date:
        from datetime import date as date_class
        if v > date_class.today():
            raise ValueError("end_date 不能为未来日期")
        return v


class RegenerateResponse(BaseModel):
    regenerated: int = 0
    message: str


class UndoRequest(BaseModel):
    report_type: str = Field(..., pattern="^(daily|monthly)$")
    stat_date: date


class UndoResponse(BaseModel):
    undone: bool = True
    message: str
    previous_total_amount: Decimal = Decimal("0")
    current_total_amount: Decimal = Decimal("0")


class CorrectionItem(BaseModel):
    id: int
    report_type: str
    stat_date: date
    old_total_amount: Optional[Decimal] = None
    new_total_amount: Optional[Decimal] = None
    corrected_by_name: Optional[str] = None
    reason: Optional[str] = None
    is_undo: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class CorrectionListResponse(BaseModel):
    items: List[CorrectionItem]
    total: int = 0
