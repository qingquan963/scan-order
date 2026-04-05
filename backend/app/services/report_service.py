"""
Phase 3C Report Service
负责报表数据聚合、归档、修正、撤销等核心业务逻辑
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, case
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
import logging

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.dish import Dish
from app.models.daily_revenue import DailyRevenue
from app.models.monthly_revenue import MonthlyRevenue
from app.models.report_correction import ReportCorrection
from app.models.merchant_user import MerchantUser

logger = logging.getLogger(__name__)


class ReportService:
    """报表服务"""

    # ─── 实时聚合 ─────────────────────────────────────────────────────────

    @staticmethod
    def aggregate_orders_for_date(
        db: Session,
        merchant_id: int,
        stat_date: date,
    ) -> Dict[str, Any]:
        """
        从 orders 表实时聚合指定日期的营收数据
        """
        start = datetime.combine(stat_date, datetime.min.time())
        end = datetime.combine(stat_date + timedelta(days=1), datetime.min.time())

        # 主表统计
        order_stats = db.query(
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_amount"),
            func.sum(case((Order.status == "paid", 1), else_=0)).label("paid_count"),
            func.sum(case((Order.status == "cancelled", 1), else_=0)).label("cancelled_count"),
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status.in_(["paid", "completed", "cancelled"])
        ).first()

        total_orders = order_stats.total_orders or 0
        total_amount = Decimal(str(order_stats.total_amount or 0))
        paid_count = order_stats.paid_count or 0
        cancelled_count = order_stats.cancelled_count or 0

        # 菜品总份数
        dish_result = db.query(
            func.coalesce(func.sum(OrderItem.quantity), 0)
        ).join(Order).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status.in_(["paid", "completed", "cancelled"])
        ).scalar() or 0

        total_dishes = int(dish_result)

        # 客单价
        avg_order_amount = total_amount / total_orders if total_orders > 0 else Decimal("0")

        # 支付方式统计（默认 cash_orders = paid_count）
        cash_orders = paid_count
        credit_orders = 0

        # 优惠抵扣（Phase 3B 字段，暂无数据）
        coupon_discount = Decimal("0")
        points_discount = Decimal("0")

        # 顾客统计（使用 customer_name 作为顾客标识）
        customer_subq = db.query(
            Order.customer_name,
            func.min(Order.created_at).label("first_visit"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status.in_(["paid", "completed", "cancelled"]),
            Order.customer_name.isnot(None),
            Order.customer_name != "",
        ).group_by(Order.customer_name).subquery()

        all_customers = db.query(customer_subq).all()
        new_customers = sum(1 for c in all_customers if c.order_count == 1)
        returning_customers = sum(1 for c in all_customers if c.order_count > 1)

        return {
            "total_orders": total_orders,
            "total_amount": total_amount,
            "total_dishes": total_dishes,
            "avg_order_amount": avg_order_amount,
            "paid_count": paid_count,
            "cancelled_count": cancelled_count,
            "cash_orders": cash_orders,
            "credit_orders": credit_orders,
            "coupon_discount": coupon_discount,
            "points_discount": points_discount,
            "new_customers": new_customers,
            "returning_customers": returning_customers,
        }

    # ─── 日报查询 ─────────────────────────────────────────────────────────

    @staticmethod
    def get_daily_report(
        db: Session,
        merchant_id: int,
        start_date: date,
        end_date: date,
        page: int = 1,
        page_size: int = 31,
    ) -> Tuple[List[Dict], Dict, int]:
        """
        获取日报列表，支持双轨读取
        """
        today = date.today()
        items = []
        total_records = 0

        if end_date < today:
            # 全历史，直接读归档
            query = db.query(DailyRevenue).filter(
                DailyRevenue.merchant_id == merchant_id,
                DailyRevenue.stat_date >= start_date,
                DailyRevenue.stat_date <= end_date,
                DailyRevenue.is_finalized == 1,
            ).order_by(DailyRevenue.stat_date.desc())

            total_records = query.count()
            for dr in query.offset((page - 1) * page_size).limit(page_size).all():
                items.append(ReportService._dr_to_dict(dr))

            summary = ReportService._compute_summary(items)
            return items, summary, total_records

        else:
            # 含今日：历史归档 + 今日实时
            hist_end = today - timedelta(days=1)

            if start_date <= hist_end:
                hist_query = db.query(DailyRevenue).filter(
                    DailyRevenue.merchant_id == merchant_id,
                    DailyRevenue.stat_date >= start_date,
                    DailyRevenue.stat_date <= hist_end,
                    DailyRevenue.is_finalized == 1,
                ).order_by(DailyRevenue.stat_date.desc())

                total_records = hist_query.count()
                for dr in hist_query.all():
                    items.append(ReportService._dr_to_dict(dr))

            # 今日实时部分
            if end_date >= today:
                today_data = ReportService.aggregate_orders_for_date(db, merchant_id, today)
                today_data["stat_date"] = today
                today_data["is_finalized"] = 0
                items.insert(0, today_data)
                total_records += 1

            # 分页（仅对历史部分）
            if page > 1:
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                items = items[start_idx:end_idx]

            summary = ReportService._compute_summary(items)
            return items, summary, total_records

    @staticmethod
    def _dr_to_dict(dr: DailyRevenue) -> Dict:
        return {
            "stat_date": dr.stat_date,
            "total_orders": dr.total_orders,
            "total_amount": dr.total_amount,
            "avg_order_amount": dr.avg_order_amount,
            "paid_count": dr.paid_count,
            "cancelled_count": dr.cancelled_count,
            "cash_orders": dr.cash_orders,
            "credit_orders": dr.credit_orders,
            "coupon_discount": dr.coupon_discount,
            "points_discount": dr.points_discount,
            "new_customers": dr.new_customers,
            "returning_customers": dr.returning_customers,
            "is_finalized": dr.is_finalized,
        }

    @staticmethod
    def _compute_summary(items: List[Dict]) -> Dict:
        total_orders = sum(item.get("total_orders", 0) for item in items)
        total_amount = sum(Decimal(str(item.get("total_amount", 0))) for item in items)
        avg_order = total_amount / total_orders if total_orders > 0 else Decimal("0")
        return {
            "total_orders": total_orders,
            "total_amount": total_amount,
            "avg_order_amount": avg_order,
        }

    # ─── 月报查询 ─────────────────────────────────────────────────────────

    @staticmethod
    def get_monthly_report(
        db: Session,
        merchant_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> Tuple[List[Dict], Dict]:
        today = date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month - 1 if today.month > 1 else 12
            if month == today.month - 1 and year == today.year:
                pass
            else:
                if month == 12:
                    year = today.year - 1

        items = []

        query = db.query(MonthlyRevenue).filter(
            MonthlyRevenue.merchant_id == merchant_id,
            MonthlyRevenue.is_finalized == 1,
        ).order_by(MonthlyRevenue.stat_year.desc(), MonthlyRevenue.stat_month.desc())

        all_months = query.all()
        for mr in all_months:
            if mr.stat_year == today.year and mr.stat_month == today.month:
                month_start = date(today.year, today.month, 1)
                month_end = today
                daily_data = ReportService._aggregate_daily_range(
                    db, merchant_id, month_start, month_end
                )
                items.append({
                    "stat_year": today.year,
                    "stat_month": today.month,
                    **daily_data,
                    "is_finalized": 0,
                })
            else:
                items.append({
                    "stat_year": mr.stat_year,
                    "stat_month": mr.stat_month,
                    "total_orders": mr.total_orders,
                    "total_amount": mr.total_amount,
                    "avg_order_amount": mr.avg_order_amount,
                    "paid_count": mr.paid_count,
                    "cancelled_count": mr.cancelled_count,
                    "cash_orders": mr.cash_orders,
                    "credit_orders": mr.credit_orders,
                    "coupon_discount": mr.coupon_discount,
                    "points_discount": mr.points_discount,
                    "new_customers": mr.new_customers,
                    "returning_customers": mr.returning_customers,
                    "is_finalized": mr.is_finalized,
                })

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = items[start_idx:end_idx]

        summary = ReportService._compute_summary(items)
        return paged_items, summary

    @staticmethod
    def _aggregate_daily_range(
        db: Session,
        merchant_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict:
        result = db.query(
            func.sum(DailyRevenue.total_orders).label("total_orders"),
            func.sum(DailyRevenue.total_amount).label("total_amount"),
            func.sum(DailyRevenue.total_dishes).label("total_dishes"),
            func.sum(DailyRevenue.paid_count).label("paid_count"),
            func.sum(DailyRevenue.cancelled_count).label("cancelled_count"),
            func.sum(DailyRevenue.cash_orders).label("cash_orders"),
            func.sum(DailyRevenue.credit_orders).label("credit_orders"),
            func.sum(DailyRevenue.coupon_discount).label("coupon_discount"),
            func.sum(DailyRevenue.points_discount).label("points_discount"),
            func.sum(DailyRevenue.new_customers).label("new_customers"),
            func.sum(DailyRevenue.returning_customers).label("returning_customers"),
        ).filter(
            DailyRevenue.merchant_id == merchant_id,
            DailyRevenue.stat_date >= start_date,
            DailyRevenue.stat_date <= end_date,
        ).first()

        total_orders = result.total_orders or 0
        total_amount = Decimal(str(result.total_amount or 0))
        avg_order = total_amount / total_orders if total_orders > 0 else Decimal("0")

        return {
            "total_orders": total_orders,
            "total_amount": total_amount,
            "avg_order_amount": avg_order,
            "total_dishes": result.total_dishes or 0,
            "paid_count": result.paid_count or 0,
            "cancelled_count": result.cancelled_count or 0,
            "cash_orders": result.cash_orders or 0,
            "credit_orders": result.credit_orders or 0,
            "coupon_discount": Decimal(str(result.coupon_discount or 0)),
            "points_discount": Decimal(str(result.points_discount or 0)),
            "new_customers": result.new_customers or 0,
            "returning_customers": result.returning_customers or 0,
        }

    # ─── 菜品销量排行 ─────────────────────────────────────────────────────

    @staticmethod
    def get_dish_ranking(
        db: Session,
        merchant_id: int,
        start_date: date,
        end_date: date,
        limit: int = 20,
    ) -> Tuple[List[Dict], Dict]:
        from app.models.category import Category  # noqa: F401
        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

        results = db.query(
            OrderItem.dish_id,
            Dish.name.label("dish_name"),
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_amount"),
            func.count(func.distinct(Order.id)).label("order_count"),
            func.avg(OrderItem.unit_price).label("avg_price"),
        ).join(Order).join(Dish, OrderItem.dish_id == Dish.id).join(
            Category, Dish.category_id == Category.id
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status.in_(["paid", "completed"]),
        ).group_by(
            OrderItem.dish_id, Dish.name, Category.name,
        ).order_by(
            desc("total_quantity"),
        ).limit(limit).all()

        items = []
        total_dish_quantity = 0
        for r in results:
            items.append({
                "dish_id": r.dish_id,
                "dish_name": r.dish_name,
                "category_name": r.category_name,
                "total_quantity": r.total_quantity,
                "total_amount": Decimal(str(r.total_amount or 0)),
                "order_count": r.order_count,
                "avg_price": Decimal(str(r.avg_price or 0)),
            })
            total_dish_quantity += r.total_quantity

        summary = {
            "total_dish_types": len(items),
            "total_dish_quantity": total_dish_quantity,
        }
        return items, summary

    # ─── 顾客分析 ─────────────────────────────────────────────────────────

    @staticmethod
    def get_customer_analysis(
        db: Session,
        merchant_id: int,
        start_date: date,
        end_date: date,
        sort_by: str = "total_amount",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], Dict, int]:
        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

        subq = db.query(
            Order.customer_name.label("customer_key"),
            Order.customer_name.label("nickname"),
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_amount).label("total_amount"),
            func.avg(Order.total_amount).label("avg_order_amount"),
            func.max(Order.created_at).label("last_visit"),
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status.in_(["paid", "completed"]),
            Order.customer_name.isnot(None),
            Order.customer_name != "",
        ).group_by(Order.customer_name).subquery()

        # sort_col must reference subquery columns (subq.c.*), not Order model,
        # because the ORDER BY is applied against the subquery result set.
        sort_map = {
            "total_amount": subq.c.total_amount,
            "visit_count": subq.c.total_orders,
            "total_orders": subq.c.total_orders,
        }
        sort_col = sort_map.get(sort_by, subq.c.total_amount)

        total = db.query(func.count()).select_from(subq).scalar() or 0

        if order == "desc":
            q = db.query(subq).order_by(desc(sort_col))
        else:
            from sqlalchemy import asc
            q = db.query(subq).order_by(asc(sort_col))

        customers = q.offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for c in customers:
            items.append({
                "customer_key": c.customer_key or "未知",
                "nickname": c.customer_key or "匿名顾客",
                "avatar_url": None,
                "visit_count": c.total_orders or 0,
                "total_orders": c.total_orders or 0,
                "total_amount": Decimal(str(c.total_amount or 0)),
                "avg_order_amount": Decimal(str(c.avg_order_amount or 0)),
                "last_visit": c.last_visit,
                "tier_name": "普通会员",
                "total_points": 0,
                "new_customer": False,
            })

        total_amount_sum = sum(Decimal(str(c.total_amount or 0)) for c in customers)
        total_orders_sum = sum(c.total_orders or 0 for c in customers)
        avg_total = total_amount_sum / len(customers) if customers else Decimal("0")
        avg_orders = Decimal(str(total_orders_sum / len(customers) if customers else 0))

        summary = {
            "avg_total_per_customer": avg_total,
            "avg_orders_per_customer": avg_orders,
        }
        return items, summary, total

    # ─── 顾客群体画像 ─────────────────────────────────────────────────────

    @staticmethod
    def get_customer_segments(
        db: Session,
        merchant_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict:
        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        today = date.today()

        # 总顾客数
        total_customers = db.query(
            func.count(func.distinct(Order.customer_name))
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= start,
            Order.created_at < end,
            Order.status.in_(["paid", "completed"]),
            Order.customer_name.isnot(None),
            Order.customer_name != "",
        ).scalar() or 0

        # 今日新客
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        new_today = db.query(
            func.count(func.distinct(Order.customer_name))
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= today_start,
            Order.created_at < today_end,
            Order.status.in_(["paid", "completed"]),
            Order.customer_name.isnot(None),
        ).scalar() or 0

        # 本月新客
        month_start = date(today.year, today.month, 1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        new_this_month = db.query(
            func.count(func.distinct(Order.customer_name))
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= month_start_dt,
            Order.created_at < today_end,
            Order.status.in_(["paid", "completed"]),
            Order.customer_name.isnot(None),
        ).scalar() or 0

        # 本月活跃顾客
        active_this_month = db.query(
            func.count(func.distinct(Order.customer_name))
        ).filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= month_start_dt,
            Order.created_at < today_end,
            Order.status.in_(["paid", "completed"]),
            Order.customer_name.isnot(None),
        ).scalar() or 0

        # 30天不活跃
        inactive_30d_start = today - timedelta(days=30)
        inactive_30d = db.query(
            func.count()
        ).select_from(
            db.query(
                Order.customer_name,
                func.max(Order.created_at).label("last_visit"),
            ).filter(
                Order.merchant_id == merchant_id,
                Order.status.in_(["paid", "completed"]),
                Order.customer_name.isnot(None),
            ).group_by(Order.customer_name).subquery()
        ).filter(
            func.date(
                db.query(
                    Order.customer_name,
                    func.max(Order.created_at).label("last_visit"),
                ).filter(
                    Order.merchant_id == merchant_id,
                    Order.status.in_(["paid", "completed"]),
                    Order.customer_name.isnot(None),
                ).group_by(Order.customer_name).subquery().c.last_visit
            ) < inactive_30d_start
        ).scalar() or 0

        # 简化版：总顾客 - 活跃顾客
        inactive_30d = max(0, total_customers - active_this_month)

        return {
            "total_customers": total_customers,
            "new_today": new_today,
            "new_this_month": new_this_month,
            "active_this_month": active_this_month,
            "inactive_30d": inactive_30d,
            "tier_distribution": [
                {"tier": "普通会员", "count": total_customers, "percentage": 100.0}
            ],
            "avg_points_per_customer": Decimal("0"),
            "avg_visit_per_customer": 0.0,
        }

    # ─── 手动修正 ─────────────────────────────────────────────────────────

    @staticmethod
    def regenerate_report(
        db: Session,
        merchant_id: int,
        report_type: str,
        start_date: date,
        end_date: date,
        corrected_by: int,
        reason: Optional[str] = None,
    ) -> int:
        if report_type == "daily":
            # 检查已归档数据
            finalized = db.query(DailyRevenue).filter(
                DailyRevenue.merchant_id == merchant_id,
                DailyRevenue.stat_date >= start_date,
                DailyRevenue.stat_date <= end_date,
                DailyRevenue.is_finalized == 1,
            ).first()
            if finalized:
                raise PermissionError("包含已归档数据，不允许手动修正（需联系平台管理员）")

            current_date = start_date
            regenerated_count = 0
            while current_date <= end_date:
                old_record = db.query(DailyRevenue).filter(
                    DailyRevenue.merchant_id == merchant_id,
                    DailyRevenue.stat_date == current_date,
                ).first()
                old_amount = old_record.total_amount if old_record else None

                data = ReportService.aggregate_orders_for_date(db, merchant_id, current_date)

                if old_record:
                    for key, value in data.items():
                        setattr(old_record, key, value)
                    old_record.version = (old_record.version or 0) + 1
                else:
                    new_record = DailyRevenue(
                        merchant_id=merchant_id,
                        stat_date=current_date,
                        **data,
                        is_finalized=0,
                        version=0,
                    )
                    db.add(new_record)

                correction = ReportCorrection(
                    merchant_id=merchant_id,
                    report_type="daily",
                    stat_date=current_date,
                    old_total_amount=old_amount,
                    new_total_amount=data["total_amount"],
                    corrected_by=corrected_by,
                    reason=reason,
                    is_undo=0,
                )
                db.add(correction)

                regenerated_count += 1
                current_date += timedelta(days=1)

            db.commit()
            ReportService._recalc_monthly_from_daily(db, merchant_id, start_date, end_date)
            return regenerated_count

        elif report_type == "monthly":
            year = start_date.year
            month = start_date.month

            finalized = db.query(MonthlyRevenue).filter(
                MonthlyRevenue.merchant_id == merchant_id,
                MonthlyRevenue.stat_year == year,
                MonthlyRevenue.stat_month == month,
                MonthlyRevenue.is_finalized == 1,
            ).first()
            if finalized:
                raise PermissionError("该月报已归档，不允许手动修正（需联系平台管理员）")

            old_record = db.query(MonthlyRevenue).filter(
                MonthlyRevenue.merchant_id == merchant_id,
                MonthlyRevenue.stat_year == year,
                MonthlyRevenue.stat_month == month,
            ).first()
            old_amount = old_record.total_amount if old_record else None

            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            data = ReportService._aggregate_daily_range(db, merchant_id, month_start, month_end)

            if old_record:
                for key, value in data.items():
                    setattr(old_record, key, value)
                old_record.version = (old_record.version or 0) + 1
            else:
                new_record = MonthlyRevenue(
                    merchant_id=merchant_id,
                    stat_year=year,
                    stat_month=month,
                    **data,
                    is_finalized=0,
                    version=0,
                )
                db.add(new_record)

            correction = ReportCorrection(
                merchant_id=merchant_id,
                report_type="monthly",
                stat_date=month_start,
                old_total_amount=old_amount,
                new_total_amount=data["total_amount"],
                corrected_by=corrected_by,
                reason=reason,
                is_undo=0,
            )
            db.add(correction)

            db.commit()
            return 1

        raise ValueError(f"不支持的 report_type: {report_type}")

    # ─── 撤销修正 ─────────────────────────────────────────────────────────

    @staticmethod
    def undo_correction(
        db: Session,
        merchant_id: int,
        report_type: str,
        stat_date: date,
        corrected_by: int,
    ) -> Dict:
        correction = db.query(ReportCorrection).filter(
            ReportCorrection.merchant_id == merchant_id,
            ReportCorrection.report_type == report_type,
            ReportCorrection.stat_date == stat_date,
            ReportCorrection.is_undo == 0,
        ).order_by(ReportCorrection.created_at.desc()).first()

        if not correction:
            raise ValueError("无修正记录可撤销")

        old_amount = correction.old_total_amount or Decimal("0")
        previous_amount = correction.old_total_amount

        if report_type == "daily":
            record = db.query(DailyRevenue).filter(
                DailyRevenue.merchant_id == merchant_id,
                DailyRevenue.stat_date == stat_date,
            ).first()
            if not record:
                raise ValueError("日报记录不存在")
            if record.is_finalized == 1:
                raise PermissionError("该日报已归档，无法撤销")
            current_amount = record.total_amount
            record.total_amount = old_amount
            record.version = (record.version or 0) + 1

        elif report_type == "monthly":
            year = stat_date.year
            month = stat_date.month
            record = db.query(MonthlyRevenue).filter(
                MonthlyRevenue.merchant_id == merchant_id,
                MonthlyRevenue.stat_year == year,
                MonthlyRevenue.stat_month == month,
            ).first()
            if not record:
                raise ValueError("月报记录不存在")
            if record.is_finalized == 1:
                raise PermissionError("该月报已归档，无法撤销")
            current_amount = record.total_amount
            record.total_amount = old_amount
            record.version = (record.version or 0) + 1

        undo_correction = ReportCorrection(
            merchant_id=merchant_id,
            report_type=report_type,
            stat_date=stat_date,
            old_total_amount=current_amount,
            new_total_amount=old_amount,
            corrected_by=corrected_by,
            reason="撤销修正",
            is_undo=1,
        )
        db.add(undo_correction)
        db.commit()

        if report_type == "daily":
            ReportService._recalc_monthly_from_daily(db, merchant_id, stat_date, stat_date)

        return {
            "previous_total_amount": previous_amount or Decimal("0"),
            "current_total_amount": current_amount,
        }

    # ─── 月报自动重算 ─────────────────────────────────────────────────────

    @staticmethod
    def _recalc_monthly_from_daily(
        db: Session,
        merchant_id: int,
        start_date: date,
        end_date: date,
    ):
        months = set()
        current = start_date
        while current <= end_date:
            months.add((current.year, current.month))
            current += timedelta(days=1)

        for year, month in months:
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            mr = db.query(MonthlyRevenue).filter(
                MonthlyRevenue.merchant_id == merchant_id,
                MonthlyRevenue.stat_year == year,
                MonthlyRevenue.stat_month == month,
            ).first()

            if mr and mr.is_finalized == 1:
                logger.info(f"[Phase3C] Month {year}-{month} is finalized, skipping recalc")
                continue

            data = ReportService._aggregate_daily_range(db, merchant_id, month_start, month_end)

            if mr:
                for key, value in data.items():
                    setattr(mr, key, value)
                mr.version = (mr.version or 0) + 1
            else:
                new_mr = MonthlyRevenue(
                    merchant_id=merchant_id,
                    stat_year=year,
                    stat_month=month,
                    **data,
                    is_finalized=0,
                    version=0,
                )
                db.add(new_mr)

            logger.info(f"[Phase3C] Recalculated monthly revenue for {year}-{month}")

        db.commit()

    # ─── 定时归档 ─────────────────────────────────────────────────────────

    @staticmethod
    def finalize_daily(db: Session, merchant_id: int, stat_date: date) -> bool:
        record = db.query(DailyRevenue).filter(
            DailyRevenue.merchant_id == merchant_id,
            DailyRevenue.stat_date == stat_date,
        ).first()

        if not record:
            data = ReportService.aggregate_orders_for_date(db, merchant_id, stat_date)
            record = DailyRevenue(
                merchant_id=merchant_id,
                stat_date=stat_date,
                **data,
                is_finalized=1,
                version=0,
            )
            db.add(record)
            db.commit()
            return True

        if record.is_finalized == 1:
            return False

        expected_version = record.version or 0
        result = db.query(DailyRevenue).filter(
            DailyRevenue.merchant_id == merchant_id,
            DailyRevenue.stat_date == stat_date,
            DailyRevenue.version == expected_version,
            DailyRevenue.is_finalized == 0,
        ).update({
            "is_finalized": 1,
            "version": expected_version + 1,
        })

        if result == 0:
            db.rollback()
            result = db.query(DailyRevenue).filter(
                DailyRevenue.merchant_id == merchant_id,
                DailyRevenue.stat_date == stat_date,
                DailyRevenue.is_finalized == 0,
            ).update({
                "is_finalized": 1,
                "version": (record.version or 0) + 1,
            })
            if result == 0:
                return False

        db.commit()
        return True

    @staticmethod
    def finalize_monthly(db: Session, merchant_id: int, year: int, month: int) -> bool:
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        record = db.query(MonthlyRevenue).filter(
            MonthlyRevenue.merchant_id == merchant_id,
            MonthlyRevenue.stat_year == year,
            MonthlyRevenue.stat_month == month,
        ).first()

        if record and record.is_finalized == 1:
            return False

        data = ReportService._aggregate_daily_range(db, merchant_id, month_start, month_end)
        expected_version = record.version if record else 0

        if record:
            for key, value in data.items():
                setattr(record, key, value)
            record.is_finalized = 1
            record.version = (expected_version or 0) + 1
        else:
            new_record = MonthlyRevenue(
                merchant_id=merchant_id,
                stat_year=year,
                stat_month=month,
                **data,
                is_finalized=1,
                version=0,
            )
            db.add(new_record)

        db.commit()
        return True

    # ─── 修正记录查询 ─────────────────────────────────────────────────────

    @staticmethod
    def get_corrections(
        db: Session,
        merchant_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        report_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], int]:
        query = db.query(ReportCorrection).filter(
            ReportCorrection.merchant_id == merchant_id,
        )

        if start_date:
            query = query.filter(ReportCorrection.stat_date >= start_date)
        if end_date:
            query = query.filter(ReportCorrection.stat_date <= end_date)
        if report_type and report_type != "all":
            query = query.filter(ReportCorrection.report_type == report_type)

        total = query.count()
        corrections = query.order_by(
            ReportCorrection.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for c in corrections:
            user = db.query(MerchantUser).filter(MerchantUser.id == c.corrected_by).first()
            user_name = user.username if user else f"用户{c.corrected_by}"

            items.append({
                "id": c.id,
                "report_type": c.report_type,
                "stat_date": c.stat_date,
                "old_total_amount": c.old_total_amount,
                "new_total_amount": c.new_total_amount,
                "corrected_by_name": user_name,
                "reason": c.reason,
                "is_undo": c.is_undo,
                "created_at": c.created_at,
            })

        return items, total
