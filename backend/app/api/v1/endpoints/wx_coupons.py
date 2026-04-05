"""
WeChat Customer Coupon Endpoints - Phase 3B
/api/v1/wx/coupons/*
顾客端：领取优惠券、我的优惠券、可用优惠券
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.dependencies import get_wx_customer
from app.schemas.coupon import (
    CouponClaimResponse,
    MyCouponsResponse,
    AvailableCouponResponse,
    CouponRecordResponse,
)
from app.services.coupon_service import CouponService

router = APIRouter()


@router.post("/{coupon_id}/claim", response_model=CouponClaimResponse)
def claim_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """
    领取优惠券
    使用乐观锁防止超发
    """
    customer_id = customer_info["customer_id"]
    binding_id = customer_info["binding_id"]

    record = CouponService.claim_coupon(
        db=db,
        coupon_id=coupon_id,
        customer_id=customer_id,
        binding_id=binding_id,
    )

    # 获取券信息用于返回
    from app.models.coupon import Coupon
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()

    return CouponClaimResponse(
        record_id=record.id,
        coupon_name=coupon.name if coupon else "",
        code=record.code,
        expires_at=record.expires_at,
        message="领取成功",
    )


@router.get("/my", response_model=MyCouponsResponse)
def get_my_coupons(
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """我的优惠券（按状态分组）"""
    customer_id = customer_info["customer_id"]

    result = CouponService.get_my_coupons(db, customer_id)

    unused = [CouponRecordResponse(**r) for r in result["unused"]]
    used = [CouponRecordResponse(**r) for r in result["used"]]
    expired = [CouponRecordResponse(**r) for r in result["expired"]]

    return MyCouponsResponse(unused=unused, used=used, expired=expired)


@router.get("/available", response_model=list[AvailableCouponResponse])
def get_available_coupons(
    merchant_id: Optional[int] = Query(None, description="指定商户ID，不传则返回所有商户"),
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """当前可用的优惠券（供下单页展示）"""
    customer_id = customer_info["customer_id"]
    merchant = merchant_id or customer_info["merchant_id"]

    result = CouponService.get_available_coupons(db, customer_id, merchant)
    return [AvailableCouponResponse(**r) for r in result]
