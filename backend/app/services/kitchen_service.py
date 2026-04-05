"""
Phase Kitchen - 后厨屏业务逻辑服务
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.table import DiningTable
from app.config import Settings

_settings = Settings()


class KitchenService:

    # ─── Token 管理（简单 UUID token） ─────────────────────────

    _kitchen_tokens: dict = {}  # token -> {merchant_id, expires_at}

    @classmethod
    def verify_pin(cls, pin: str) -> bool:
        """验证后厨 PIN 码"""
        return pin == _settings.KITCHEN_PIN

    @classmethod
    def generate_kitchen_token(cls, merchant_id: int) -> Tuple[str, int]:
        """生成后厨访问令牌，返回 (token, expires_in_seconds)"""
        token = secrets.token_urlsafe(32)
        expires_in = _settings.KITCHEN_TOKEN_TTL
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        cls._kitchen_tokens[token] = {
            "merchant_id": merchant_id,
            "expires_at": expires_at
        }
        return token, expires_in

    @classmethod
    def verify_kitchen_token(cls, token: str) -> Optional[int]:
        """验证后厨令牌，返回 merchant_id 或 None"""
        entry = cls._kitchen_tokens.get(token)
        if not entry:
            return None
        if datetime.utcnow() > entry["expires_at"]:
            del cls._kitchen_tokens[token]
            return None
        return entry["merchant_id"]

    # ─── 订单查询 ───────────────────────────────────────────────

    @staticmethod
    def get_kitchen_orders(
        db: Session,
        merchant_id: int,
        status: str = "preparing",
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Order], int]:
        """
        获取后厨订单列表
        - status: 'pending' / 'preparing' / 'all'
        - 按 created_at 升序（最早的在前）
        - 只返回 kitchen_status != 'completed' 的订单
        """
        query = db.query(Order).filter(
            Order.merchant_id == merchant_id,
            Order.kitchen_status != "completed"
        )

        if status and status != "all":
            query = query.filter(Order.kitchen_status == status)

        total = query.count()
        offset = (page - 1) * page_size
        orders = query.order_by(Order.created_at.asc()).offset(offset).limit(page_size).all()
        return orders, total

    # ─── 接单（乐观锁） ──────────────────────────────────────────

    @staticmethod
    def accept_order(db: Session, merchant_id: int, order_id: int) -> Tuple[Optional[Order], Optional[str]]:
        """
        厨房接单：pending → preparing
        使用乐观锁：WHERE id=:id AND kitchen_status='pending'
        返回 (order, None) 成功 或 (None, error_message) 失败
        """
        # 先查询订单
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id
        ).first()

        if not order:
            return None, "订单不存在"

        # 乐观锁：只有 pending 才能接单
        if order.kitchen_status != "pending":
            return None, f"当前状态为 {order.kitchen_status or 'NULL'}，无法接单"

        # 执行乐观锁更新
        rows = db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id,
            Order.kitchen_status == "pending"
        ).update({
            "kitchen_status": "preparing",
            "updated_at": datetime.utcnow()
        }, synchronize_session=False)

        if rows == 0:
            return None, "conflict"

        db.commit()
        db.refresh(order)
        return order, None

    # ─── 标记菜品完成 ───────────────────────────────────────────

    @staticmethod
    def mark_item_done(
        db: Session, merchant_id: int, order_id: int, item_id: int
    ) -> Tuple[Optional[OrderItem], Optional[str], bool]:
        """
        标记菜品完成：is_done = True
        同时检查是否所有菜品都完成，若是则自动 completed 订单
        返回 (item, error_message, order_all_done)
        """
        # 验证订单属于该商户
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id
        ).first()
        if not order:
            return None, "订单不存在", False

        # 获取菜品项
        item = db.query(OrderItem).filter(
            OrderItem.id == item_id,
            OrderItem.order_id == order_id
        ).first()
        if not item:
            return None, "菜品不存在", False

        # 已经是完成状态
        if item.is_done == 1:
            return item, None, False

        # 标记完成
        item.is_done = 1
        order.updated_at = datetime.utcnow()

        # 检查是否所有菜品都完成
        all_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        order_all_done = all(i.is_done == 1 for i in all_items)

        if order_all_done:
            order.kitchen_status = "completed"
            order.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(item)
        return item, None, order_all_done

    # ─── 撤销菜品完成 ───────────────────────────────────────────

    @staticmethod
    def mark_item_undone(
        db: Session, merchant_id: int, order_id: int, item_id: int
    ) -> Tuple[Optional[OrderItem], Optional[str]]:
        """
        撤销菜品完成：is_done = False
        如果订单是 completed 状态，需先重置为 preparing
        """
        # 验证订单
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id
        ).first()
        if not order:
            return None, "订单不存在"

        # 获取菜品项
        item = db.query(OrderItem).filter(
            OrderItem.id == item_id,
            OrderItem.order_id == order_id
        ).first()
        if not item:
            return None, "菜品不存在"

        # 如果订单已完成，先重置为制作中
        if order.kitchen_status == "completed":
            order.kitchen_status = "preparing"
            order.updated_at = datetime.utcnow()

        item.is_done = 0
        order.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(item)
        return item, None

    # ─── 重置订单 ───────────────────────────────────────────────

    @staticmethod
    def reset_order(
        db: Session, merchant_id: int, order_id: int
    ) -> Tuple[Optional[Order], Optional[str]]:
        """
        重置订单：kitchen_status=pending, 所有 items.is_done=False
        乐观锁：只有 preparing 才能重置
        """
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id
        ).first()
        if not order:
            return None, "订单不存在"

        if order.kitchen_status != "preparing":
            return None, f"当前状态为 {order.kitchen_status or 'NULL'}，无法重置"

        rows = db.query(Order).filter(
            Order.id == order_id,
            Order.merchant_id == merchant_id,
            Order.kitchen_status == "preparing"
        ).update({
            "kitchen_status": "pending",
            "updated_at": datetime.utcnow()
        }, synchronize_session=False)

        if rows == 0:
            return None, "conflict"

        # 重置所有菜品项
        db.query(OrderItem).filter(
            OrderItem.order_id == order_id
        ).update({"is_done": 0}, synchronize_session=False)

        db.commit()
        db.refresh(order)
        return order, None
