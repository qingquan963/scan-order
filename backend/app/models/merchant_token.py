from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class MerchantToken(Base):
    """商户用户 JWT Token 管理（支持 refresh token）"""
    __tablename__ = "merchant_tokens"

    id = Column(Integer, primary_key=True, index=True)
    merchant_user_id = Column(Integer, ForeignKey("merchant_users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    token_type = Column(String(20), nullable=False, default="access")  # access, refresh
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
