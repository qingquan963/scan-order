from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime
from app.database import Base


class AuditLog(Base):
    """数据访问审计日志"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    user_type = Column(String(20), nullable=True)  # platform_admin, merchant_user, customer
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)  # order, dish, category, etc.
    resource_id = Column(Integer, nullable=True)
    merchant_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
