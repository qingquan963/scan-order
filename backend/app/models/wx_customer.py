from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class WxCustomer(Base):
    """微信顾客基础信息"""
    __tablename__ = "wx_customers"

    id = Column(Integer, primary_key=True, index=True)
    wx_openid = Column(String(100), unique=True, nullable=False, index=True)
    wx_unionid = Column(String(100), nullable=True)
    wx_nickname = Column(String(255), nullable=True)
    wx_avatar = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bindings = relationship("WxMerchantBinding", back_populates="customer")


class WxMerchantBinding(Base):
    """顾客×商户绑定关系（积分账户）"""
    __tablename__ = "wx_merchant_bindings"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("wx_customers.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    points = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    visit_count = Column(Integer, default=0)
    last_visit = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("WxCustomer", back_populates="bindings")
    merchant = relationship("Merchant")
