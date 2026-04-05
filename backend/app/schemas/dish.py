from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DishBase(BaseModel):
    """菜品基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="菜品名称")
    description: Optional[str] = Field("", description="菜品描述")
    price: float = Field(..., gt=0, description="菜品价格")
    category_id: int = Field(..., description="分类ID")
    image_url: Optional[str] = Field("", description="图片URL")
    is_available: bool = Field(True, description="是否上架")


class DishCreate(DishBase):
    """创建菜品请求模型"""
    pass


class DishUpdate(BaseModel):
    """更新菜品请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="菜品名称")
    description: Optional[str] = Field(None, description="菜品描述")
    price: Optional[float] = Field(None, gt=0, description="菜品价格")
    category_id: Optional[int] = Field(None, description="分类ID")
    image_url: Optional[str] = Field(None, description="图片URL")
    is_available: Optional[bool] = Field(None, description="是否上架")


class DishResponse(DishBase):
    """菜品响应模型"""
    id: int
    merchant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DishToggleResponse(BaseModel):
    """切换上下架响应模型"""
    id: int
    is_available: bool
    message: str
