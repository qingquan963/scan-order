from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("dining_tables.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False,
                        default="00000000-0000-0000-0000-000000000001", index=True)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(String(20), default="pending")
    total_amount = Column(Float, default=0)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    remark = Column(Text, nullable=True, default="")
    # 支付相关字段
    payment_token = Column(String(36), nullable=True)  # UUID v4
    payment_token_used = Column(Integer, default=0)      # 0=未使用, 1=已使用
    paid_at = Column(DateTime, nullable=True)            # 结账时间
    # Phase 3B: 优惠券和积分
    coupon_discount = Column(Float, default=0)           # 优惠券减免金额
    points_discount = Column(Float, default=0)          # 积分抵扣金额
    customer_id = Column(Integer, nullable=True)        # 微信顾客ID
    binding_id = Column(Integer, nullable=True)         # wx_merchant_bindings.id
    coupon_record_id = Column(Integer, nullable=True)    # 核销的优惠券记录ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Phase Kitchen: 后厨屏状态
    kitchen_status = Column(String(20), nullable=True, default=None)  # pending / preparing / completed

    table = relationship("DiningTable", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
