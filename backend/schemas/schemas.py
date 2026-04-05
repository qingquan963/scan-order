from pydantic import BaseModels, Field
from typing import Optional, List
from datetime import datetime


# Merchant
class MerchantBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


class MerchantCreate(MerchantBase):
    pass


class MerchantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


class MerchantResponse(MerchantBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Category
class CategoryBase(BaseModel):
    name: str
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    merchant_id: int


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    merchant_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Dish
class DishBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    is_available: bool = True


class DishCreate(DishBase):
    category_id: int


class DishUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class DishResponse(DishBase):
    id: int
    category_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# DiningTable
class DiningTableBase(BaseModel):
    table_number: str


class DiningTableCreate(DiningTableBase):
    merchant_id: int


class DiningTableUpdate(BaseModel):
    status: Optional[str] = None
    qr_code: Optional[str] = None


class DiningTableResponse(DiningTableBase):
    id: int
    merchant_id: int
    qr_code: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Order
class OrderItemBase(BaseModel):
    dish_id: int
    quantity: int = 1
    note: Optional[str] = None


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    table_id: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    note: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


class OrderResponse(OrderBase):
    id: int
    order_number: str
    status: str
    total_amount: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True
