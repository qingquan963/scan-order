"""
租户模型（Phase 1: 多租户 SaaS 化）
所有业务表通过 tenant_id 关联到所属租户
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from app.database import Base


class Tenant(Base):
    """租户表 — SaaS 多商户顶层隔离单位"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)          # URL-safe 唯一标识
    tier = Column(String(20), default="trial")                       # trial/basic/standard/enterprise
    subscription_status = Column(String(20), default="active")      # active/suspended/cancelled
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tenant {self.slug} ({self.tier})>"
