from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class DailyRevenue(Base):
    """营收日报"""
    __tablename__ = "daily_revenue"
    __table_args__ = (
        UniqueConstraint("merchant_id", "stat_date", name="uq_daily_revenue_merchant_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    stat_date = Column(Date, nullable=False)

    # 订单统计
    total_orders = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0)
    total_dishes = Column(Integer, default=0)
    avg_order_amount = Column(Numeric(10, 2), default=0)

    # 状态统计
    paid_count = Column(Integer, default=0)
    cancelled_count = Column(Integer, default=0)

    # 支付方式
    cash_orders = Column(Integer, default=0)
    credit_orders = Column(Integer, default=0)

    # 优惠抵扣
    coupon_discount = Column(Numeric(10, 2), default=0)
    points_discount = Column(Numeric(10, 2), default=0)

    # 顾客统计
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)

    # 归档保护
    is_finalized = Column(Integer, default=0)  # 0=草稿, 1=已归档
    created_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=0)  # 乐观锁版本号

    # Relationships
    merchant = relationship("Merchant", back_populates="daily_revenues")
