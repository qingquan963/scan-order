from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from pydantic_settings import BaseSettings
import random
import uuid
import qrcode
import io
import base64
from datetime import datetime

from app.database import get_db
from app.models.table import DiningTable
from app.models.category import Category
from app.models.dish import Dish
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.merchant_settings import MerchantSettings

# Phase 3B: customer endpoints routers
from app.api.v1.endpoints.wx_customer import router as wx_customer_router
from app.api.v1.endpoints.wx_coupons import router as wx_coupons_router
from app.api.v1.endpoints.wx_points import router as wx_points_router
from app.api.v1.endpoints.customer_orders import router as customer_orders_router

router = APIRouter()

# Phase 3B: 顾客微信登录/个人信息
router.include_router(wx_customer_router, prefix="/wx", tags=["顾客微信"])

# Phase 3B: 顾客优惠券
router.include_router(wx_coupons_router, prefix="/wx/coupons", tags=["顾客优惠券"])

# Phase 3B: 顾客积分
router.include_router(wx_points_router, prefix="/wx/points", tags=["顾客积分"])

# Phase 3B: 顾客订单（含券/积分）
router.include_router(customer_orders_router, tags=["顾客订单"])

# 获取 FRONTEND_PUBLIC_URL 配置
class CustomerSettings(BaseSettings):
    FRONTEND_PUBLIC_URL: Optional[str] = None


# --- Customer-facing simplified schemas ---

class CustomerOrderItemCreate(BaseModel):
    dish_id: int
    quantity: int = Field(ge=1, default=1)
    note: Optional[str] = None


class CustomerOrderCreate(BaseModel):
    table_id: int
    items: List[CustomerOrderItemCreate]
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    remark: Optional[str] = None


# --- Public endpoints (no auth required) ---

@router.get("/merchants/{merchant_id}/settings")
def get_merchant_settings(merchant_id: int, db: Session = Depends(get_db)):
    """获取商户公开设置（无需认证，带Cache-Control头）"""
    settings = db.query(MerchantSettings).filter(
        MerchantSettings.merchant_id == merchant_id
    ).first()

    if not settings:
        # 返回默认值
        return Response(
            content='{"mode":"counter_pay"}',
            media_type="application/json",
            headers={"Cache-Control": "max-age=60"}
        )

    import json
    return Response(
        content=json.dumps({"mode": settings.mode}),
        media_type="application/json",
        headers={"Cache-Control": "max-age=60"}
    )


# --- Endpoints ---

@router.get("/tables/{table_id}")
def get_table(table_id: int, db: Session = Depends(get_db)):
    table = db.query(DiningTable).filter(DiningTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="桌台不存在")
    return {"id": table.id, "code": table.code, "name": table.name, "capacity": table.capacity}


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).order_by(Category.sort_order).all()
    return [{"id": c.id, "name": c.name, "sort_order": c.sort_order} for c in cats]


@router.get("/dishes")
def list_dishes(category_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Dish)
    if category_id is not None:
        query = query.filter(Dish.category_id == category_id)
    dishes = query.all()
    return [{
        "id": d.id,
        "name": d.name,
        "description": d.description or "",
        "price": d.price,
        "image_url": d.image_url or "",
        "category_id": d.category_id,
        "is_available": 1 if d.is_available else 0
    } for d in dishes]


def _get_merchant_payment_mode(db: Session, merchant_id: int) -> str:
    """获取商户支付模式"""
    settings = db.query(MerchantSettings).filter(
        MerchantSettings.merchant_id == merchant_id
    ).first()
    return settings.mode if settings else "counter_pay"


@router.post("/orders")
def create_order(order_data: CustomerOrderCreate, db: Session = Depends(get_db)):
    # 校验桌台
    table = db.query(DiningTable).filter(DiningTable.id == order_data.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="桌台不存在")

    # 获取商户支付模式
    payment_mode = _get_merchant_payment_mode(db, table.merchant_id)

    # 生成订单号
    now = datetime.now()
    order_no = now.strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 9999):04d}"

    # 计算总价并构建订单项
    total = 0.0
    order_items = []
    for item in order_data.items:
        dish = db.query(Dish).filter(Dish.id == item.dish_id, Dish.is_available == True).first()
        if not dish:
            raise HTTPException(status_code=404, detail=f"菜品ID {item.dish_id} 不存在或已下架")
        subtotal = round(dish.price * item.quantity, 2)
        total += subtotal
        order_items.append(OrderItem(
            dish_id=dish.id,
            dish_name=dish.name,
            unit_price=dish.price,
            quantity=item.quantity,
            subtotal=subtotal,
            note=item.note or ""
        ))

    # Phase 2: 根据支付模式决定初始状态
    if payment_mode == "counter_pay":
        initial_status = "pending_payment"
        payment_token = str(uuid.uuid4())
    else:
        initial_status = "pending"
        payment_token = None

    order = Order(
        merchant_id=table.merchant_id,
        table_id=order_data.table_id,
        order_number=order_no,
        status=initial_status,
        total_amount=round(total, 2),
        remark=order_data.remark or "",
        customer_name=order_data.customer_name or "",
        customer_phone=order_data.customer_phone or "",
        payment_token=payment_token,
        payment_token_used=0,
    )
    db.add(order)
    db.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)

    db.commit()
    db.refresh(order)

    response = {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "total_amount": order.total_amount,
    }

    # counter_pay 模式返回额外支付信息
    if payment_mode == "counter_pay":
        response["payment_mode"] = "counter_pay"
        response["payment_code"] = f"ORDER-{order.id}-{payment_token[:8].upper()}"
        response["payment_token"] = payment_token

    return response


@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    response = {
        "id": order.id,
        "merchant_id": order.merchant_id,
        "order_number": order.order_number,
        "status": order.status,
        "total_amount": order.total_amount,
        "remark": order.remark or "",
        "table_id": order.table_id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "items": [{
            "id": item.id,
            "dish_name": item.dish_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "subtotal": item.subtotal,
            "note": item.note or ""
        } for item in order.items]
    }
    # 如果是 counter_pay 待支付状态，返回支付码
    if order.status == "pending_payment" and order.payment_token:
        response["payment_code"] = f"ORDER-{order.id}-{order.payment_token[:8].upper()}"
        response["payment_token"] = order.payment_token
    return response


@router.post("/orders/{order_id}/pay")
def confirm_payment(order_id: int, db: Session = Depends(get_db)):
    """
    模拟支付确认（counter_pay 模式使用）
    需要提供正确的 payment_token 才能确认支付
    Phase 3B: 支付成功后异步发放积分
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status != "pending_payment":
        raise HTTPException(status_code=400, detail=f"当前状态 {order.status} 不支持支付")

    if order.payment_token_used:
        raise HTTPException(status_code=400, detail="支付令牌已使用")

    # 生成支付码并标记为已使用
    payment_code = f"ORDER-{order.id}-{order.payment_token[:8].upper()}"
    order.status = "pending"  # 转为待接单
    order.payment_token_used = 1
    order.paid_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    # Phase 3B: 如果有 binding_id，同步发放积分
    if order.binding_id and order.customer_id:
        try:
            from app.services.points_service import PointsService
            paid_amount = float(order.total_amount)
            PointsService.award_points_sync(
                db=db,
                binding_id=order.binding_id,
                paid_amount=paid_amount,
                merchant_id=order.merchant_id,
            )
        except Exception as e:
            # 积分发放失败不影响订单状态（异步重试由后台任务处理）
            print(f"[CRON] confirm_payment points award failed for order {order_id}: {e}")

    db.commit()
    db.refresh(order)

    return {
        "success": True,
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "message": "支付确认成功，请等待商户接单"
    }
