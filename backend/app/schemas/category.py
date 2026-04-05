from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    """分类基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    sort_order: int = Field(default=0, description="排序顺序")


class CategoryCreate(CategoryBase):
    """创建分类请求模型"""
    pass


class CategoryUpdate(BaseModel):
    """更新分类请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="分类名称")
    sort_order: Optional[int] = Field(None, description="排序顺序")


class CategoryResponse(CategoryBase):
    """分类响应模型"""
    id: int
    merchant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
