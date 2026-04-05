"""
Customer Order Endpoints - Phase 3B
/api/v1/customer/member/orders
顾客端：创建订单（支持优惠券和积分抵扣）、查询订单
"""
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.database import get_db
from app.dependencies import get_wx_customer
from app.models.table import DiningTable
from app.models.dish import Dish
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.merchant_settings import MerchantSettings
from app.models.coupon import CouponRecord
from app.schemas.wx_customer import CustomerOrderCreate
from app.services.coupon_service import CouponService
from app.services.points_service import PointsService

router = APIRouter(prefix="/member")


def _generate_order_number() -> str:
    now = datetime.utcnow()
    return now.strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 9999):04d}"


@router.post("/orders")
def create_order(
    order_data: CustomerOrderCreate,
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """
    创建订单（含优惠券核销和积分扣减）
    全流程在同一数据库事务中完成，任何一步失败全部回滚
    """
    customer_id = customer_info["customer_id"]
    binding_id = customer_info["binding_id"]
    merchant_id = customer_info["merchant_id"]

    # 获取商户支付模式
    settings = db.query(MerchantSettings).filter(
        MerchantSettings.merchant_id == merchant_id
    ).first()
    payment_mode = settings.mode if settings else "counter_pay"

    # ====== 事务开始 ======
    try:
        # 1. 校验桌台
        table = db.query(DiningTable).filter(
            DiningTable.id == order_data.table_id,
            DiningTable.merchant_id == merchant_id,
        ).first()
        if not table:
            raise HTTPException(status_code=404, detail="桌台不存在")

        # 2. 计算总价并构建订单项
        total = 0.0
        order_items = []
        for item in order_data.items:
            dish = db.query(Dish).filter(
                Dish.id == item.dish_id,
                Dish.merchant_id == merchant_id,
                Dish.is_available == True,
            ).first()
            if not dish:
                raise HTTPException(status_code=404, detail=f"菜品ID {item.dish_id} 不存在或已下架")
            subtotal = round(float(dish.price) * item.quantity, 2)
            total += subtotal
            order_items.append({
                "dish_id": dish.id,
                "dish_name": dish.name,
                "unit_price": dish.price,
                "quantity": item.quantity,
                "subtotal": subtotal,
                "note": item.note or "",
            })

        order_amount = round(total, 2)
        coupon_discount = 0.0
        points_discount = 0.0
        coupon_record_id = None

        # 3. 校验并核销优惠券（如果有）
        if order_data.coupon_record_id:
            record, coupon, discount = CouponService.validate_coupon_for_order(
                db=db,
                record_id=order_data.coupon_record_id,
                binding_id=binding_id,
                merchant_id=merchant_id,
                order_amount=order_amount,
            )
            coupon_discount = discount
            coupon_record_id = order_data.coupon_record_id

        # 计算折后金额（用于积分校验）
        discounted_amount = order_amount - coupon_discount

        # 4. 校验并扣减积分（如果有）
        if order_data.use_points and order_data.use_points > 0:
            can_use, max_pts, max_disc, msg = PointsService.validate_points_usage(
                db=db,
                binding_id=binding_id,
                use_points=order_data.use_points,
                order_amount=discounted_amount,
                merchant_id=merchant_id,
            )
            if not can_use:
                raise HTTPException(status_code=400, detail=msg)

            points_discount = PointsService.compute_points_discount(
                order_data.use_points, discounted_amount
            )
            points_discount = round(points_discount, 2)

            # 积分扣减（乐观锁）
            success = PointsService.deduct_points(
                db=db,
                binding_id=binding_id,
                use_points=order_data.use_points,
            )
            if not success:
                raise HTTPException(status_code=409, detail="积分扣减失败，请重试")

        # 最终订单金额
        final_amount = round(order_amount - coupon_discount - points_discount, 2)
        if final_amount < 0:
            final_amount = 0

        # 5. 生成订单号和状态
        order_number = _generate_order_number()
        if payment_mode == "counter_pay":
            initial_status = "pending_payment"
        else:
            initial_status = "pending"

        # 6. 创建订单
        order = Order(
            merchant_id=merchant_id,
            table_id=order_data.table_id,
            order_number=order_number,
            status=initial_status,
            total_amount=final_amount,
            customer_name=order_data.customer_name or "",
            customer_phone=order_data.customer_phone or "",
            remark=order_data.remark or "",
            coupon_discount=coupon_discount,
            points_discount=points_discount,
            customer_id=customer_id,
            binding_id=binding_id,
            coupon_record_id=coupon_record_id,
            payment_token_used=0,
            # Phase Kitchen: credit_pay 模式创建即 pending，进入后厨待接单
            kitchen_status="pending" if initial_status == "pending" else None,
        )
        db.add(order)
        db.flush()  # 获取 order.id

        # 7. 核销优惠券（如果有）
        if order_data.coupon_record_id:
            # 使用乐观锁 version 字段
            record_for_redeem = db.query(CouponRecord).filter(
                CouponRecord.id == order_data.coupon_record_id
            ).first()
            if not record_for_redeem:
                raise HTTPException(status_code=404, detail="优惠券记录不存在")

            success = CouponService.redeem_coupon(
                db=db,
                record_id=order_data.coupon_record_id,
                order_id=order.id,
                expected_version=record_for_redeem.version,
            )
            if not success:
                raise HTTPException(status_code=409, detail="优惠券已被使用，请重新选择")

        # 8. 创建订单项
        for item_data in order_items:
            order_item = OrderItem(
                order_id=order.id,
                dish_id=item_data["dish_id"],
                dish_name=item_data["dish_name"],
                unit_price=item_data["unit_price"],
                quantity=item_data["quantity"],
                subtotal=item_data["subtotal"],
                note=item_data["note"],
            )
            db.add(order_item)

        # ====== 事务提交 ======
        db.commit()
        db.refresh(order)

        response = {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
            "coupon_discount": coupon_discount,
            "points_discount": points_discount,
            "order_number_display": order.order_number,
        }

        if payment_mode == "counter_pay":
            response["payment_mode"] = "counter_pay"
            response["payment_code"] = f"ORDER-{order.id}-{order_number[-8:].upper()}"
            response["payment_token"] = order.payment_token

        return response

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
def list_orders(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """顾客订单列表"""
    customer_id = customer_info["customer_id"]

    query = db.query(Order).filter(
        Order.customer_id == customer_id,
        Order.merchant_id == customer_info["merchant_id"],
    )
    if status:
        query = query.filter(Order.status == status)

    total = query.count()
    offset = (page - 1) * limit
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
            "coupon_discount": order.coupon_discount,
            "points_discount": order.points_discount,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        })

    return {"total": total, "orders": result}


@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    customer_info: dict = Depends(get_wx_customer),
):
    """顾客订单详情"""
    customer_id = customer_info["customer_id"]

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == customer_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "total_amount": order.total_amount,
        "coupon_discount": order.coupon_discount,
        "points_discount": order.points_discount,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "items": [
            {
                "dish_name": item.dish_name,
                "unit_price": item.unit_price,
                "quantity": item.quantity,
                "subtotal": item.subtotal,
            }
            for item in order.items
        ],
    }
