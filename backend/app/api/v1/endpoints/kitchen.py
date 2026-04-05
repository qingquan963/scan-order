"""
Phase Kitchen - 后厨屏 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.kitchen_service import KitchenService
from app.schemas.kitchen import (
    KitchenAuthRequest,
    KitchenAuthResponse,
    KitchenOrderListResponse,
    KitchenOrderResponse,
    KitchenItemResponse,
    KitchenAcceptResponse,
    KitchenItemDoneResponse,
    KitchenConflictResponse,
    KitchenErrorResponse,
)
from app.models.merchant import Merchant

router = APIRouter()


# ─── 依赖：验证后厨令牌 ────────────────────────────────────────

def get_kitchen_merchant(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Merchant:
    """验证后厨访问令牌，返回商户对象"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少后厨访问令牌")

    token = authorization[7:]  # 去掉 "Bearer " 前缀
    merchant_id = KitchenService.verify_kitchen_token(token)

    if merchant_id is None:
        raise HTTPException(status_code=401, detail="无效或已过期的后厨令牌")

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="商户不存在")

    return merchant


# ─── 路由 ────────────────────────────────────────────────────

@router.post("/auth", response_model=KitchenAuthResponse)
def kitchen_auth(
    auth_req: KitchenAuthRequest,
    db: Session = Depends(get_db)
):
    """
    后厨 PIN 码验证，获取访问令牌
    """
    if not KitchenService.verify_pin(auth_req.pin):
        raise HTTPException(status_code=401, detail="PIN 码错误")

    # PIN 验证成功后，生成 token
    # 使用一个默认的 merchant_id=1（实际应由前端指定商户，或通过其他方式获取）
    # 这里取 db 中第一个商户用于演示，生产环境应通过其他方式关联商户
    from app.models.merchant import Merchant
    merchant = db.query(Merchant).first()
    if not merchant:
        raise HTTPException(status_code=500, detail="系统中没有商户，请先配置")

    token, expires_in = KitchenService.generate_kitchen_token(merchant.id)
    return KitchenAuthResponse(token=token, expires_in=expires_in)


@router.get("/orders", response_model=KitchenOrderListResponse)
def get_kitchen_orders(
    status: str = Query("preparing", description="筛选状态：pending/preparing/all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_kitchen_merchant)
):
    """
    获取后厨订单列表
    """
    orders, total = KitchenService.get_kitchen_orders(
        db=db,
        merchant_id=merchant.id,
        status=status,
        page=page,
        page_size=page_size
    )

    order_responses = []
    for order in orders:
        # 获取桌台号
        table_number = ""
        if order.table:
            table_number = order.table.code or order.table.name or str(order.table_id)

        items = []
        for item in order.items:
            items.append(KitchenItemResponse(
                id=item.id,
                dish_name=item.dish_name,
                quantity=item.quantity,
                note=item.note,
                is_done=bool(item.is_done)
            ))

        order_responses.append(KitchenOrderResponse(
            id=order.id,
            order_number=order.order_number,
            table_number=table_number,
            kitchen_status=order.kitchen_status,
            created_at=order.created_at,
            updated_at=order.updated_at,
            remark=order.remark,
            items=items
        ))

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return KitchenOrderListResponse(
        orders=order_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.put("/orders/{order_id}/accept", response_model=KitchenAcceptResponse)
def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_kitchen_merchant)
):
    """
    厨房接单：pending → preparing
    """
    order, err = KitchenService.accept_order(db, merchant.id, order_id)

    if err == "conflict":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": "订单状态已被其他屏幕修改，请刷新重试",
                "current_kitchen_status": order.kitchen_status if order else None
            }
        )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return KitchenAcceptResponse(
        id=order.id,
        kitchen_status=order.kitchen_status,
        updated_at=order.updated_at,
        message="已接单"
    )


@router.put("/orders/{order_id}/items/{item_id}/done", response_model=KitchenItemDoneResponse)
def mark_item_done(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_kitchen_merchant)
):
    """
    标记菜品完成
    """
    item, err, order_all_done = KitchenService.mark_item_done(
        db, merchant.id, order_id, item_id
    )

    if err == "conflict":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": "订单状态已被其他屏幕修改，请刷新重试"
            }
        )
    if err:
        raise HTTPException(status_code=400, detail=err)

    # 获取最新的 updated_at
    order = db.query(Order).filter(Order.id == order_id).first()
    updated_at = order.updated_at if order else item.order.updated_at

    return KitchenItemDoneResponse(
        item_id=item.id,
        is_done=True,
        order_id=order_id,
        order_all_done=order_all_done,
        updated_at=updated_at
    )


@router.put("/items/{item_id}/undone")
def mark_item_undone(
    item_id: int,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_kitchen_merchant)
):
    """
    撤销菜品完成
    """
    # 先通过 item 找到 order_id
    item = db.query(OrderItem).filter(OrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="菜品不存在")

    order_id = item.order_id

    result, err = KitchenService.mark_item_undone(
        db, merchant.id, order_id, item_id
    )

    if err:
        raise HTTPException(status_code=400, detail=err)

    order = db.query(Order).filter(Order.id == order_id).first()

    return {
        "item_id": item_id,
        "is_done": False,
        "order_id": order_id,
        "updated_at": order.updated_at if order else None
    }


@router.put("/orders/{order_id}/reset")
def reset_order(
    order_id: int,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_kitchen_merchant)
):
    """
    重置订单到待接单状态
    """
    order, err = KitchenService.reset_order(db, merchant.id, order_id)

    if err == "conflict":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": "订单状态已被其他屏幕修改，请刷新重试"
            }
        )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "id": order.id,
        "kitchen_status": order.kitchen_status,
        "updated_at": order.updated_at,
        "message": "订单已重置"
    }
