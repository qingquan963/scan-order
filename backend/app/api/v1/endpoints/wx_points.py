"""
WeChat Customer Points Endpoints - Phase 3B
/api/v1/wx/points/*
顾客端：积分明细
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_wx_customer
from app.schemas.points import PointsHistoryResponse, PointsHistoryItem
from app.services.points_service import PointsService

router = APIRouter()


@router.get("/history", response_model=PointsHistoryResponse)
def get_points_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """
    积分明细
    Phase 3B: 从 orders 表聚合
    Phase 4: 使用独立的 points_history 物理表
    """
    binding_id = customer_info["binding_id"]
    merchant_id = customer_info["merchant_id"]

    result = PointsService.get_points_history(
        db=db,
        binding_id=binding_id,
        merchant_id=merchant_id,
        page=page,
        limit=limit,
    )

    items = [PointsHistoryItem(**item) for item in result["items"]]
    result["items"] = items

    return PointsHistoryResponse(**result)


@router.get("/preview")
def get_points_preview(
    order_amount: float,
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """下单前积分预览（可抵扣多少）"""
    binding_id = customer_info["binding_id"]
    merchant_id = customer_info["merchant_id"]

    # 获取当前积分余额
    account = PointsService.get_points_account(db, customer_info["customer_id"], merchant_id)
    balance_points = account["points"]

    # 获取最大可用积分
    can_use, max_points, max_discount, msg = PointsService.validate_points_usage(
        db=db,
        binding_id=binding_id,
        use_points=balance_points,
        order_amount=order_amount,
        merchant_id=merchant_id,
    )

    return {
        "can_use_points": can_use,
        "max_points_usable": max_points,
        "max_discount_amount": max_discount,
        "balance_points": balance_points,
        "message": msg,
    }
