from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Coupon(Base):
    """优惠券模板表"""
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # cash=满减券, discount=折扣券
    threshold = Column(Numeric(10, 2), default=0)
    discount_value = Column(Numeric(10, 2), nullable=False)
    total_count = Column(Integer, nullable=False)
    issued_count = Column(Integer, default=0)
    per_user_limit = Column(Integer, default=1)
    valid_days = Column(Integer, default=30)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")  # active, paused, expired
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant")
    records = relationship("CouponRecord", back_populates="coupon")


class CouponRecord(Base):
    """优惠券领取/核销记录表"""
    __tablename__ = "coupon_records"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("wx_customers.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    binding_id = Column(Integer, ForeignKey("wx_merchant_bindings.id"), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(20), default="unused")  # unused, used, expired
    issued_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    used_order_id = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    version = Column(Integer, default=0)

    coupon = relationship("Coupon", back_populates="records")
    customer = relationship("WxCustomer")
    merchant = relationship("Merchant")
    binding = relationship("WxMerchantBinding")

    __table_args__ = (
        UniqueConstraint("binding_id", "used_order_id", name="uq_binding_order"),
    )


class CouponClaimLock(Base):
    """优惠券发放分布式锁表（备用）"""
    __tablename__ = "coupon_claim_lock"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), unique=True, nullable=False)
    lock_token = Column(String(64), unique=True, nullable=False)
    acquired_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    coupon = relationship("Coupon")
