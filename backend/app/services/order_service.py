from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.dish import Dish
from app.models.table import DiningTable
from app.schemas.order import OrderCreate, OrderUpdate, OrderStatusUpdate
from app.utils.order_no import generate_order_number
import random


class OrderService:
    @staticmethod
    def create_order(db: Session, merchant_id: int, order_data: OrderCreate) -> Order:
        """创建订单"""
        # 验证桌台是否存在且属于该商户
        table = db.query(DiningTable).filter(
            DiningTable.id == order_data.table_id,
            DiningTable.merchant_id == merchant_id
        ).first()
        
        if not table:
            raise ValueError("桌台不存在或不属于当前商户")
        
        # 生成订单号
        order_number = generate_order_number()
        
        # 计算总金额
        total_amount = sum(item.subtotal for item in order_data.items)
        
        # 创建订单
        db_order = Order(
            merchant_id=merchant_id,
            table_id=order_data.table_id,
            order_number=order_number,
            status="pending",
            total_amount=total_amount,
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            remark=order_data.remark,
            # Phase Kitchen: 新订单自动进入后厨待接单
            kitchen_status="pending"
        )
        
        db.add(db_order)
        db.flush()  # 获取order_id
        
        # 创建订单项
        for item_data in order_data.items:
            # 验证菜品是否存在
            dish = db.query(Dish).filter(
                Dish.id == item_data.dish_id,
                Dish.merchant_id == merchant_id
            ).first()
            
            if not dish:
                raise ValueError(f"菜品ID {item_data.dish_id} 不存在或不属于当前商户")
            
            order_item = OrderItem(
                order_id=db_order.id,
                dish_id=item_data.dish_id,
                dish_name=item_data.dish_name,
                unit_price=item_data.unit_price,
                quantity=item_data.quantity,
                subtotal=item_data.subtotal,
                note=item_data.note
            )
            db.add(order_item)
        
        db.commit()
        db.refresh(db_order)
        return db_order
    
    @staticmethod
    def get_orders(
        db: Session, 
        merchant_id: int, 
        status: Optional[str] = None,
        page: int = 1, 
        limit: int = 20
    ) -> Tuple[List[Order], int]:
        """获取订单列表（支持分页和状态筛选）"""
        query = db.query(Order).filter(Order.merchant_id == merchant_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * limit
        orders = query.order_by(desc(Order.created_at)).offset(offset).limit(limit).all()
        
        return orders, total
    
    @staticmethod
    def get_merchant_payment_mode(db: Session, merchant_id: int) -> str:
        """获取商户支付模式"""
        from app.models.merchant_settings import MerchantSettings
        settings = db.query(MerchantSettings).filter(
            MerchantSettings.merchant_id == merchant_id
        ).first()
        return settings.mode if settings else "counter_pay"
    
    @staticmethod
    def get_order_by_id(db: Session, merchant_id: int, order_id: int) -> Optional[Order]:
        """根据ID获取订单（包含订单项）"""
        return db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id
        ).first()
    
    @staticmethod
    def update_order_status(
        db: Session, 
        merchant_id: int, 
        order_id: int, 
        status_update: OrderStatusUpdate
    ) -> Optional[Order]:
        """更新订单状态"""
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id
        ).first()
        
        if not order:
            return None
        
        # 状态流转校验（Phase 2: paid 为终态，禁止转换）
        valid_transitions = {
            "pending": ["confirmed", "cancelled"],
            "pending_payment": ["pending", "cancelled"],  # counter_pay: 支付后→pending，取消→cancelled
            "confirmed": ["paid", "cancelled"],
            "paid": [],  # 已结账为终态，禁止转换
            "cancelled": []  # 已取消的订单不能再更改状态
        }
        
        current_status = order.status
        new_status = status_update.status
        
        if new_status not in valid_transitions.get(current_status, []):
            raise ValueError(f"不能从状态 {current_status} 转换到 {new_status}")
        
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # Phase 2: 当状态转为 paid 时记录结账时间
        if new_status == "paid":
            order.paid_at = datetime.utcnow()

        # Phase Kitchen: pending_payment -> pending 时进入后厨待接单
        if current_status == "pending_payment" and new_status == "pending":
            order.kitchen_status = "pending"
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def get_today_stats(db: Session, merchant_id: int) -> dict:
        """获取今日经营概览"""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # 今日所有订单
        today_orders = db.query(Order).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= today,
            Order.created_at < tomorrow
        ).all()
        
        # 统计
        total_orders = len(today_orders)
        total_revenue = sum(order.total_amount for order in today_orders)
        completed_orders = sum(1 for order in today_orders if order.status == "paid")
        pending_orders = sum(1 for order in today_orders if order.status == "pending")
        cancelled_orders = sum(1 for order in today_orders if order.status == "cancelled")
        
        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "cancelled_orders": cancelled_orders
        }
    
    @staticmethod
    def get_sales_stats(db: Session, merchant_id: int, range_type: str = "day") -> dict:
        """获取销售统计"""
        today = date.today()
        
        if range_type == "day":
            # 最近7天
            start_date = today - timedelta(days=6)
            date_format = "%Y-%m-%d"
            group_by = func.date(Order.created_at)
        elif range_type == "week":
            # 最近4周
            start_date = today - timedelta(weeks=3)
            date_format = "%Y-W%W"
            group_by = func.strftime("%Y-W%W", Order.created_at)
        elif range_type == "month":
            # 最近6个月
            start_date = today - timedelta(days=180)
            date_format = "%Y-%m"
            group_by = func.strftime("%Y-%m", Order.created_at)
        else:
            raise ValueError("range_type 必须是 'day', 'week' 或 'month'")
        
        # 查询统计数据
        stats_query = db.query(
            group_by.label("period"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_amount")
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= start_date,
            Order.status == "paid"  # 只统计已支付的订单
        ).group_by(group_by).order_by(group_by)
        
        stats = stats_query.all()
        
        # 格式化数据
        data = []
        total_revenue = 0
        total_orders = 0
        
        for stat in stats:
            period = stat.period
            order_count = stat.order_count or 0
            total_amount = stat.total_amount or 0
            
            data.append({
                "period": period,
                "orders": order_count,
                "revenue": total_amount,
                "average": total_amount / order_count if order_count > 0 else 0
            })
            
            total_revenue += total_amount
            total_orders += order_count
        
        return {
            "period": range_type,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "average_order_value": total_revenue / total_orders if total_orders > 0 else 0,
            "data": data
        }