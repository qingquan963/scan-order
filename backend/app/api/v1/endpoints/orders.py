from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.dependencies import get_current_merchant
from app.models.merchant import Merchant
from app.schemas.order import (
    OrderResponse, 
    OrderListResponse, 
    OrderStatusUpdate,
    TodayStatsResponse,
    SalesStatsResponse
)
from app.services.order_service import OrderService

router = APIRouter()


@router.get("/orders", response_model=OrderListResponse)
def get_orders(
    status: Optional[str] = Query(None, description="订单状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取订单列表（支持状态筛选和分页）"""
    try:
        orders, total = OrderService.get_orders(
            db=db,
            merchant_id=current_merchant.id,
            status=status,
            page=page,
            limit=limit
        )
        
        # 获取商户支付模式
        payment_mode = OrderService.get_merchant_payment_mode(db, current_merchant.id)
        
        # 为每个订单添加 payment_mode 和 paid_at 字段
        orders_with_payment = []
        for order in orders:
            order_dict = {
                "id": order.id,
                "merchant_id": order.merchant_id,
                "table_id": order.table_id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": order.total_amount,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "remark": order.remark,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "payment_token": order.payment_token,
                "paid_at": order.paid_at,
                "items": order.items,
                # Phase 2: 新增字段
                "payment_mode": payment_mode,
            }
            # 动态构造 OrderResponse
            orders_with_payment.append(order_dict)
        
        # 构建 OrderResponse 列表
        order_responses = []
        from app.schemas.order import OrderResponse as OrdResp
        for od in orders_with_payment:
            try:
                order_responses.append(OrdResp(**od))
            except Exception:
                # 兼容没有 items 的情况
                from app.schemas.order import OrderItemResponse
                items = []
                for item in od.get("items", []):
                    items.append(OrderItemResponse.model_validate(item))
                od["items"] = items
                order_responses.append(OrdResp(**od))
        
        return OrderListResponse(
            total=total,
            page=page,
            limit=limit,
            orders=order_responses
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取订单详情"""
    order = OrderService.get_order_by_id(
        db=db,
        merchant_id=current_merchant.id,
        order_id=order_id
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # Phase 2: 添加 payment_mode 和 paid_at
    payment_mode = OrderService.get_merchant_payment_mode(db, current_merchant.id)
    
    # 直接返回 OrderResponse，利用 from_attributes=True 自动映射
    order.payment_mode = payment_mode  # 动态添加属性
    return order


@router.put("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """更新订单状态"""
    try:
        order = OrderService.update_order_status(
            db=db,
            merchant_id=current_merchant.id,
            order_id=order_id,
            status_update=status_update
        )
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/today", response_model=TodayStatsResponse)
def get_today_stats(
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取今日经营概览"""
    try:
        stats = OrderService.get_today_stats(
            db=db,
            merchant_id=current_merchant.id
        )
        
        return TodayStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/sales", response_model=SalesStatsResponse)
def get_sales_stats(
    range_type: str = Query("day", description="统计范围: day, week, month"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取销售统计"""
    try:
        stats = OrderService.get_sales_stats(
            db=db,
            merchant_id=current_merchant.id,
            range_type=range_type
        )
        
        return SalesStatsResponse(**stats)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}/ticket")
def get_order_ticket(
    order_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取订单小票文本"""
    order = OrderService.get_order_by_id(
        db=db,
        merchant_id=current_merchant.id,
        order_id=order_id
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 生成小票文本
    lines = []
    lines.append("=" * 32)
    lines.append("        消 费 小 票")
    lines.append("=" * 32)
    lines.append(f"订单号: {order.order_number}")
    lines.append(f"桌号:   {order.table.name if order.table else order.table_id}")
    if order.customer_name:
        lines.append(f"顾客:   {order.customer_name}")
    lines.append("-" * 32)
    lines.append("商品明细:")
    for item in order.items:
        lines.append(f"  {item.dish_name}")
        lines.append(f"    {item.unit_price:.2f} x {item.quantity} = {item.subtotal:.2f}")
        if item.note:
            lines.append(f"    备注: {item.note}")
    lines.append("-" * 32)
    lines.append(f"合计:       ¥{order.total_amount:.2f}")
    lines.append(f"订单状态: {order.status}")
    lines.append(f"下单时间: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if order.remark:
        lines.append(f"备注: {order.remark}")
    lines.append("=" * 32)
    lines.append("        谢谢惠顾!")
    lines.append("=" * 32)
    
    return {"ticket": "\n".join(lines)}