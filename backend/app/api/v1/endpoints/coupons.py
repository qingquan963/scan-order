"""
Admin Coupon Management Endpoints - Phase 3B
/api/v1/admin/coupons/*
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.dependencies import get_current_merchant
from app.models.merchant import Merchant
from app.models.wx_customer import WxCustomer
from app.schemas.coupon import (
    CouponCreate, CouponResponse, CouponListResponse,
    CouponRecordAdminResponse, CouponRecordAdminListResponse,
)
from app.services.coupon_service import CouponService

router = APIRouter()


@router.post("/coupons", response_model=CouponResponse, status_code=201)
def create_coupon(
    coupon_data: CouponCreate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """创建优惠券（需 owner 角色）"""
    coupon = CouponService.create_coupon(
        db=db,
        merchant_id=current_merchant.id,
        name=coupon_data.name,
        coupon_type=coupon_data.type,
        threshold=coupon_data.threshold,
        discount_value=coupon_data.discount_value,
        total_count=coupon_data.total_count,
        per_user_limit=coupon_data.per_user_limit,
        valid_days=coupon_data.valid_days,
        start_time=coupon_data.start_time,
        end_time=coupon_data.end_time,
    )
    return coupon


@router.get("/coupons", response_model=CouponListResponse)
def list_coupons(
    status: Optional[str] = Query(None, description="状态筛选: active/paused/expired"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """优惠券列表"""
    coupons = CouponService.get_coupons(db, current_merchant.id, status=status)
    return CouponListResponse(total=len(coupons), coupons=coupons)


@router.get("/coupons/{coupon_id}", response_model=CouponResponse)
def get_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """获取优惠券详情"""
    coupon = CouponService.get_coupon_by_id(db, coupon_id, current_merchant.id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    return coupon


@router.get("/coupons/{coupon_id}/records", response_model=CouponRecordAdminListResponse)
def get_coupon_records(
    coupon_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """优惠券核销明细"""
    records, total = CouponService.get_coupon_records(
        db, coupon_id, current_merchant.id, page=page, limit=limit
    )

    result_records = []
    for record in records:
        # 获取顾客昵称
        customer = db.query(WxCustomer).filter(WxCustomer.id == record.customer_id).first()
        customer_nickname = customer.wx_nickname if customer else None

        result_records.append(CouponRecordAdminResponse(
            id=record.id,
            customer_nickname=customer_nickname,
            status=record.status,
            issued_at=record.issued_at,
            used_at=record.used_at,
            expires_at=record.expires_at,
            code=record.code,
            used_order_id=record.used_order_id,
        ))

    return CouponRecordAdminListResponse(total=total, records=result_records)


@router.post("/coupons/{coupon_id}/pause", response_model=CouponResponse)
def pause_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """暂停发放优惠券"""
    coupon = CouponService.pause_coupon(db, coupon_id, current_merchant.id)
    return coupon


@router.post("/coupons/{coupon_id}/resume", response_model=CouponResponse)
def resume_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """恢复发放优惠券"""
    coupon = CouponService.resume_coupon(db, coupon_id, current_merchant.id)
    return coupon
