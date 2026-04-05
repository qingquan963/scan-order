"""
WeChat Customer Auth Endpoints - Phase 3B
/api/v1/wx/customer/*
顾客端：微信登录、个人信息
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_wx_customer
from app.models.merchant import Merchant
from app.models.wx_customer import WxCustomer
from app.schemas.wx_customer import (
    WxCustomerLoginRequest,
    WxCustomerTokenResponse,
    CustomerMeResponse,
)
from app.services.wx_customer_service import WxCustomerService

router = APIRouter()


@router.post("/customer/login", response_model=WxCustomerTokenResponse)
async def customer_login(
    login_data: WxCustomerLoginRequest,
    db: Session = Depends(get_db),
):
    """
    顾客微信登录（小程序 code 换 token）
    返回 JWT token 和基本信息
    """
    result = await WxCustomerService.login_with_code(
        db=db,
        code=login_data.code,
        merchant_id=login_data.merchant_id,
    )
    return result


@router.get("/customer/me", response_model=CustomerMeResponse)
def get_customer_me(
    request: Request,
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """获取当前顾客信息（含积分和等级）"""
    customer_id = customer_info["customer_id"]
    binding_id = customer_info["binding_id"]
    merchant_id = customer_info["merchant_id"]

    result = WxCustomerService.get_customer_me(
        db=db,
        customer_id=customer_id,
        binding_id=binding_id,
        merchant_id=merchant_id,
    )
    return CustomerMeResponse(**result)
