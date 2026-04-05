from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MerchantSettings(Base):
    __tablename__ = "merchant_settings"

    merchant_id = Column(Integer, ForeignKey("merchants.id"), primary_key=True)
    mode = Column(String(50), default="counter_pay", nullable=False)
    # Phase 3B: 积分配置
    points_enabled = Column(Integer, default=1)          # 0=关闭积分, 1=开启积分
    points_per_yuan = Column(Integer, default=1)        # 每消费1元获得的积分数
    points_max_discount_percent = Column(Integer, default=50)  # 积分最多抵扣订单金额的百分比
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="settings")
