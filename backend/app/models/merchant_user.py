from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MerchantUser(Base):
    """商户用户（owner/staff 角色分离）"""
    __tablename__ = "merchant_users"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    username = Column(String(50), nullable=True)  # nullable for WeChat-only users
    password_hash = Column(String(255), nullable=True)  # nullable for WeChat-only users
    wx_openid = Column(String(100), unique=True, nullable=True)
    wx_unionid = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default="owner")  # owner, staff
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    merchant = relationship("Merchant", back_populates="users")
