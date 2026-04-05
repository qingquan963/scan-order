from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class WxAuthState(Base):
    """微信 OAuth state 管理（10分钟有效期）"""
    __tablename__ = "wx_auth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(64), unique=True, nullable=False, index=True)
    redirect_uri = Column(String(500), nullable=True)
    merchant_user_id = Column(Integer, ForeignKey("merchant_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


class WxRefreshToken(Base):
    """微信 refresh token（30天有效期）"""
    __tablename__ = "wx_refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    merchant_user_id = Column(Integer, ForeignKey("merchant_users.id"), nullable=False)
    refresh_token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
