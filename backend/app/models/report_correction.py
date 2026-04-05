from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric, Text
from datetime import datetime
from app.database import Base


class ReportCorrection(Base):
    """报表修正日志"""
    __tablename__ = "report_corrections"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    report_type = Column(String(20), nullable=False)  # 'daily' or 'monthly'
    stat_date = Column(Date, nullable=False)  # 月报填当月第一天
    old_total_amount = Column(Numeric(12, 2), nullable=True)
    new_total_amount = Column(Numeric(12, 2), nullable=True)
    corrected_by = Column(Integer, ForeignKey("merchant_users.id"), nullable=False)
    reason = Column(Text, nullable=True)
    is_undo = Column(Integer, default=0)  # 0=正常修正, 1=撤销操作
    created_at = Column(DateTime, default=datetime.utcnow)
