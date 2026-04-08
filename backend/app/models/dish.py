from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False,
                        default="00000000-0000-0000-0000-000000000001", index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True, default="")
    price = Column(Float, nullable=False)
    image_url = Column(Text, nullable=True, default="")
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="dishes")
    order_items = relationship("OrderItem", back_populates="dish")
