from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    dish_name = Column(String(100), nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    subtotal = Column(Float, nullable=False)
    note = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    # Phase Kitchen: 菜品完成状态
    is_done = Column(Integer, default=0, nullable=False)  # 0=未完成, 1=已完成

    order = relationship("Order", back_populates="items")
    dish = relationship("Dish", back_populates="order_items")
