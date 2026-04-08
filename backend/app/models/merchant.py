from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    # Phase 1: 多租户 — 固定指向默认租户（迁移后支持多租户时改为可配置）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False,
                        default="00000000-0000-0000-0000-000000000001", index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True, default="")
    address = Column(String(200), nullable=True, default="")
    phone = Column(String(20), nullable=True, default="")
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), default="active")  # pending, active, suspended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    categories = relationship("Category", back_populates="merchant")
    tables = relationship("DiningTable", back_populates="merchant")
    settings = relationship("MerchantSettings", back_populates="merchant", uselist=False)
    users = relationship("MerchantUser", back_populates="merchant", cascade="all, delete-orphan")

    # Phase 3C: 报表关系
    daily_revenues = relationship("DailyRevenue", back_populates="merchant", cascade="all, delete-orphan")
    monthly_revenues = relationship("MonthlyRevenue", back_populates="merchant", cascade="all, delete-orphan")
