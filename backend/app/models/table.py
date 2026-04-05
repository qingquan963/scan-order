from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class DiningTable(Base):
    __tablename__ = "dining_tables"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    code = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(100), default="")
    capacity = Column(Integer, default=4)
    status = Column(String(20), default="available")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="tables")
    orders = relationship("Order", back_populates="table")
