from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    categories = relationship("Category", back_populates="merchant")
    tables = relationship("DiningTable", back_populates="merchant")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    merchant = relationship("Merchant", back_populates="categories")
    dishes = relationship("Dish", back_populates="category")


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="dishes")
    order_items = relationship("OrderItem", back_populates="dish")


class DiningTable(Base):
    __tablename__ = "dining_tables"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    table_number = Column(String(20), nullable=False)
    qr_code = Column(String(500), nullable=True)
    status = Column(String(20), default="available")  # available, occupied, reserved
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    merchant = relationship("Merchant", back_populates="tables")
    orders = relationship("Order", back_populates="table")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("dining_tables.id"), nullable=False)
    order_number = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), default="pending")  # pending, confirmed, preparing, served, completed, cancelled
    total_amount = Column(Float, default=0)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    table = relationship("DiningTable", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="items")
    dish = relationship("Dish", back_populates="order_items")
