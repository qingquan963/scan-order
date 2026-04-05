from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TableBase(BaseModel):
    """桌台基础模型"""
    code: str = Field(..., min_length=1, max_length=20, description="桌台编码")
    name: str = Field(..., min_length=1, max_length=100, description="桌台名称")
    capacity: int = Field(default=4, gt=0, description="容纳人数")
    status: str = Field(default="available", description="状态: available, occupied, reserved")


class TableCreate(TableBase):
    """创建桌台请求模型"""
    pass


class TableUpdate(BaseModel):
    """更新桌台请求模型"""
    code: Optional[str] = Field(None, min_length=1, max_length=20, description="桌台编码")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="桌台名称")
    capacity: Optional[int] = Field(None, gt=0, description="容纳人数")
    status: Optional[str] = Field(None, description="状态: available, occupied, reserved")


class TableResponse(TableBase):
    """桌台响应模型"""
    id: int
    merchant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True