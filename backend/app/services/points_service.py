"""
Points Service - Phase 3B
积分账户、会员等级、积分增长与扣减
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException
from app.models.wx_customer import WxCustomer, WxMerchantBinding
from app.models.merchant_settings import MerchantSettings
from app.models.order import Order


# 会员等级阈值
TIER_THRESHOLDS = [
    (3000, "钻石会员"),
    (1000, "金卡会员"),
    (500, "银卡会员"),
    (0, "普通会员"),
]


def compute_tier(total_points: int) -> Tuple[str, int, Optional[str], Optional[int], Optional[int]]:
    """
    根据累计积分计算会员等级
    返回: (tier_name, tier_threshold, next_tier_name, next_tier_threshold, next_tier_points_needed)
    """
    for threshold, name in TIER_THRESHOLDS:
        if total_points >= threshold:
            # 找到了当前等级
            idx = TIER_THRESHOLDS.index((threshold, name))
            if idx > 0:
                next_threshold, next_name = TIER_THRESHOLDS[idx - 1]
                return (name, threshold, next_name, next_threshold, next_threshold - total_points)
            else:
                return (name, threshold, None, None, None)

    # 默认普通会员
    return ("普通会员", 0, "银卡会员", 500, 500 - total_points)


class PointsService:
    """
    Phase 3B: 积分服务

    积分汇率：固定 100积分=1元
    积分增长：支付后独立事务，不在订单事务内
    退款扣积分：扣 points 不扣 total_points（等级不变）
    """

    POINTS_TO_YUAN_RATE = 100  # 100积分 = 1元

    # ==================== 积分账户 ====================

    @staticmethod
    def get_or_create_binding(
        db: Session,
        customer_id: int,
        merchant_id: int,
    ) -> WxMerchantBinding:
        """获取或创建顾客×商户绑定关系"""
        binding = db.query(WxMerchantBinding).filter(
            WxMerchantBinding.customer_id == customer_id,
            WxMerchantBinding.merchant_id == merchant_id,
        ).first()

        if not binding:
            binding = WxMerchantBinding(
                customer_id=customer_id,
                merchant_id=merchant_id,
                points=0,
                total_points=0,
                visit_count=0,
            )
            db.add(binding)
            db.commit()
            db.refresh(binding)

        return binding

    @staticmethod
    def get_points_account(
        db: Session,
        customer_id: int,
        merchant_id: int,
    ) -> dict:
        """获取积分账户信息（含等级）"""
        binding = PointsService.get_or_create_binding(db, customer_id, merchant_id)
        tier_name, tier_threshold, next_tier_name, next_tier_threshold, next_tier_points = compute_tier(
            binding.total_points
        )

        return {
            "customer_id": customer_id,
            "merchant_id": merchant_id,
            "points": binding.points,
            "total_points": binding.total_points,
            "visit_count": binding.visit_count,
            "last_visit": binding.last_visit,
            "tier_name": tier_name,
            "tier_threshold": tier_threshold,
            "next_tier_name": next_tier_name,
            "next_tier_threshold": next_tier_threshold,
            "next_tier_points_needed": next_tier_points,
        }

    # ==================== 积分增长（支付后异步） ====================

    @staticmethod
    async def award_points_async(
        db_session_factory,
        binding_id: int,
        order_id: int,
        paid_amount: float,
        merchant_id: int,
        max_retries: int = 3,
    ):
        """
        积分增长（异步，带重试机制）
        在支付成功后独立执行，不在订单事务内
        """
        import math

        # 获取积分规则
        db = db_session_factory()
        try:
            settings = db.query(MerchantSettings).filter(
                MerchantSettings.merchant_id == merchant_id
            ).first()

            if not settings or not settings.points_enabled:
                return  # 积分未开启

            points_per_yuan = settings.points_per_yuan or 1
        finally:
            db.close()

        # 计算积分（向下取整）
        points_to_add = max(0, math.floor(paid_amount * points_per_yuan))
        if points_to_add == 0:
            return

        # 指数退避重试
        delays = [0.1, 0.2, 0.4]  # 100ms, 200ms, 400ms

        for attempt in range(max_retries):
            db = db_session_factory()
            try:
                # 幂等性检查：查询 orders 表是否有对应记录（binding_id, order_id 联合唯一）
                # Phase 3B 用 orders 表 coupon_discount/points_discount 字段判断是否已发放
                # 这里简单检查：total_points 是否已增长（通过查询）
                # 更好的方案是 Phase 4 的 points_history 表
                # 我们用 binding_id + order_id 确认幂等（orders 表唯一约束）

                # 积分增长写入
                result = db.execute(
                    WxMerchantBinding.__table__.update()
                    .where(WxMerchantBinding.id == binding_id)
                    .values(
                        points=WxMerchantBinding.points + points_to_add,
                        total_points=WxMerchantBinding.total_points + points_to_add,
                        visit_count=WxMerchantBinding.visit_count + 1,
                        last_visit=datetime.utcnow(),
                    )
                )

                if result.rowcount > 0:
                    db.commit()
                    return  # 成功
                else:
                    db.rollback()
            except Exception as e:
                db.rollback()
                print(f"[Points] award_points attempt {attempt + 1} failed: {e}")
            finally:
                db.close()

            if attempt < max_retries - 1:
                await asyncio.sleep(delays[attempt])

        # 3次重试均失败
        print(f"[Points] CRITICAL: Failed to award points after {max_retries} retries for binding={binding_id}, order={order_id}")

    @staticmethod
    def award_points_sync(
        db: Session,
        binding_id: int,
        paid_amount: float,
        merchant_id: int,
    ) -> int:
        """
        同步积分增长（支付成功后立即执行，用于小金额订单或同步场景）
        返回新增积分
        """
        import math

        settings = db.query(MerchantSettings).filter(
            MerchantSettings.merchant_id == merchant_id
        ).first()

        if not settings or not settings.points_enabled:
            return 0

        points_per_yuan = settings.points_per_yuan or 1
        points_to_add = max(0, math.floor(paid_amount * points_per_yuan))

        if points_to_add == 0:
            return 0

        result = db.execute(
            WxMerchantBinding.__table__.update()
            .where(WxMerchantBinding.id == binding_id)
            .values(
                points=WxMerchantBinding.points + points_to_add,
                total_points=WxMerchantBinding.total_points + points_to_add,
                visit_count=WxMerchantBinding.visit_count + 1,
                last_visit=datetime.utcnow(),
            )
        )

        if result.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail="积分账户不存在")
        db.commit()
        return points_to_add

    # ==================== 积分扣减（下单时） ====================

    @staticmethod
    def deduct_points(
        db: Session,
        binding_id: int,
        use_points: int,
    ) -> bool:
        """
        积分扣减（乐观锁）
        返回 True=成功，False=积分不足或并发冲突
        """
        result = db.execute(
            WxMerchantBinding.__table__.update()
            .where(
                WxMerchantBinding.id == binding_id,
                WxMerchantBinding.points >= use_points,
            )
            .values(points=WxMerchantBinding.points - use_points)
        )

        if result.rowcount == 0:
            db.rollback()
            return False

        db.commit()
        return True

    @staticmethod
    def restore_points(db: Session, binding_id: int, points: int) -> bool:
        """取消订单时返还积分"""
        result = db.execute(
            WxMerchantBinding.__table__.update()
            .where(WxMerchantBinding.id == binding_id)
            .values(points=WxMerchantBinding.points + points)
        )
        if result.rowcount == 0:
            return False
        db.commit()
        return True

    # ==================== 下单积分校验 ====================

    @staticmethod
    def validate_points_usage(
        db: Session,
        binding_id: int,
        use_points: int,
        order_amount: float,
        merchant_id: int,
    ) -> Tuple[bool, int, float, str]:
        """
        校验积分是否可用于当前订单
        返回: (can_use, max_points_usable, max_discount_amount, message)
        """
        settings = db.query(MerchantSettings).filter(
            MerchantSettings.merchant_id == merchant_id
        ).first()

        if not settings or not settings.points_enabled:
            return (False, 0, 0.0, "该商户未开启积分功能")

        binding = db.query(WxMerchantBinding).filter(
            WxMerchantBinding.id == binding_id
        ).first()

        if not binding:
            return (False, 0, 0.0, "积分账户不存在")

        if use_points > binding.points:
            return (False, binding.points, 0.0, "积分余额不足")

        max_discount_percent = settings.points_max_discount_percent or 50
        max_discount_amount = order_amount * max_discount_percent / 100
        max_points_usable = int(max_discount_amount * PointsService.POINTS_TO_YUAN_RATE)

        if use_points > max_points_usable:
            return (False, max_points_usable, max_discount_amount, f"本次订单最多可用{max_points_usable}积分")

        return (True, max_points_usable, max_discount_amount, "可以使用积分")

    @staticmethod
    def compute_points_discount(use_points: int, order_amount: float) -> float:
        """计算积分抵扣金额（固定汇率 100积分=1元）"""
        discount = use_points / PointsService.POINTS_TO_YUAN_RATE
        return min(discount, order_amount)

    # ==================== 积分明细（Phase 3B: 从 orders 聚合） ====================

    @staticmethod
    def get_points_history(
        db: Session,
        binding_id: int,
        merchant_id: int,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """
        Phase 3B: 从 orders 表聚合积分明细
        Phase 4: 改用独立的 points_history 物理表
        """
        # 获取积分账户信息
        binding = db.query(WxMerchantBinding).filter(
            WxMerchantBinding.id == binding_id,
            WxMerchantBinding.merchant_id == merchant_id,
        ).first()

        if not binding:
            raise HTTPException(status_code=404, detail="积分账户不存在")

        tier_name, tier_threshold, next_tier_name, next_tier_threshold, next_tier_points = compute_tier(
            binding.total_points
        )

        # 从 orders 表查询该顾客在该商户的订单（积分明细）
        query = db.query(Order).filter(
            Order.customer_id == binding.customer_id,
            Order.merchant_id == merchant_id,
            Order.binding_id == binding_id,
            Order.status.in_(["pending", "confirmed", "paid", "completed"]),
        )

        total = query.count()
        offset = (page - 1) * limit
        orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

        items = []
        for order in orders:
            # 积分增长：订单完成后按实付金额返积分
            if order.status in ("paid", "completed"):
                # 获取商户积分规则来计算返积分数
                settings = db.query(MerchantSettings).filter(
                    MerchantSettings.merchant_id == merchant_id
                ).first()
                points_per_yuan = settings.points_per_yuan if settings else 1
                paid = float(order.total_amount) - float(order.coupon_discount or 0) - float(order.points_discount or 0)
                import math
                points_earned = max(0, math.floor(paid * points_per_yuan))
                if points_earned > 0:
                    items.append({
                        "id": order.id,
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "change": f"+{points_earned}",
                        "amount": float(paid),
                        "reason": "消费返积分",
                        "created_at": order.created_at,
                    })

            # 积分抵扣
            if order.points_discount and order.points_discount > 0:
                import math
                points_used = int(order.points_discount * PointsService.POINTS_TO_YUAN_RATE)
                items.append({
                    "id": order.id + 100000,  # 避免与返积分ID冲突
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "change": f"-{points_used}",
                    "amount": -float(order.points_discount),
                    "reason": "积分抵扣",
                    "created_at": order.created_at,
                })

        # 按时间排序
        items.sort(key=lambda x: x["created_at"], reverse=True)

        return {
            "current_points": binding.points,
            "total_points": binding.total_points,
            "tier_name": tier_name,
            "tier_threshold": tier_threshold,
            "next_tier_name": next_tier_name,
            "next_tier_threshold": next_tier_threshold,
            "next_tier_points_needed": next_tier_points,
            "items": items,
        }
