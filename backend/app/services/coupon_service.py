"""
Coupon Service - Phase 3B
优惠券的创建、领取、核销管理
"""
import uuid
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from app.models.coupon import Coupon, CouponRecord, CouponClaimLock
from app.models.wx_customer import WxCustomer, WxMerchantBinding
from app.models.merchant_settings import MerchantSettings


class CouponService:
    # 券码前缀
    CODE_PREFIX = "CPN"

    # ==================== 商户端管理 ====================

    @staticmethod
    def create_coupon(
        db: Session,
        merchant_id: int,
        name: str,
        coupon_type: str,
        threshold: Decimal,
        discount_value: Decimal,
        total_count: int,
        per_user_limit: int = 1,
        valid_days: int = 30,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Coupon:
        """商户创建优惠券"""
        # 业务规则校验
        if coupon_type == "cash":
            if discount_value >= threshold and threshold > 0:
                raise HTTPException(
                    status_code=400,
                    detail="满减券的减免金额必须小于门槛金额"
                )

        if start_time and end_time and start_time >= end_time:
            raise HTTPException(
                status_code=400,
                detail="发行结束时间必须晚于开始时间"
            )

        coupon = Coupon(
            merchant_id=merchant_id,
            name=name,
            type=coupon_type,
            threshold=threshold,
            discount_value=discount_value,
            total_count=total_count,
            issued_count=0,
            per_user_limit=per_user_limit,
            valid_days=valid_days,
            start_time=start_time,
            end_time=end_time,
            status="active",
        )
        db.add(coupon)
        db.commit()
        db.refresh(coupon)
        return coupon

    @staticmethod
    def get_coupons(
        db: Session,
        merchant_id: int,
        status: Optional[str] = None,
    ) -> List[Coupon]:
        """获取商户优惠券列表"""
        query = db.query(Coupon).filter(Coupon.merchant_id == merchant_id)
        if status:
            query = query.filter(Coupon.status == status)
        return query.order_by(Coupon.created_at.desc()).all()

    @staticmethod
    def get_coupon_by_id(db: Session, coupon_id: int, merchant_id: int) -> Optional[Coupon]:
        return db.query(Coupon).filter(
            Coupon.id == coupon_id,
            Coupon.merchant_id == merchant_id
        ).first()

    @staticmethod
    def pause_coupon(db: Session, coupon_id: int, merchant_id: int) -> Coupon:
        """暂停发放优惠券"""
        coupon = CouponService.get_coupon_by_id(db, coupon_id, merchant_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="优惠券不存在")
        if coupon.status != "active":
            raise HTTPException(status_code=400, detail="只有生效中的优惠券可以暂停")
        coupon.status = "paused"
        db.commit()
        db.refresh(coupon)
        return coupon

    @staticmethod
    def resume_coupon(db: Session, coupon_id: int, merchant_id: int) -> Coupon:
        """恢复发放优惠券"""
        coupon = CouponService.get_coupon_by_id(db, coupon_id, merchant_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="优惠券不存在")
        if coupon.status != "paused":
            raise HTTPException(status_code=400, detail="只有暂停的优惠券可以恢复")
        coupon.status = "active"
        db.commit()
        db.refresh(coupon)
        return coupon

    # ==================== 顾客端领取 ====================

    @staticmethod
    def _generate_code() -> str:
        """生成 UUID v4 格式的券码"""
        return f"{CouponService.CODE_PREFIX}-{uuid.uuid4().hex.upper()}"

    @staticmethod
    def claim_coupon(
        db: Session,
        coupon_id: int,
        customer_id: int,
        binding_id: int,
    ) -> CouponRecord:
        """
        顾客领取优惠券（乐观锁防并发超发）
        使用 BEGIN IMMEDIATE 开启写事务
        """
        # 开始事务（SQLite IMMEDIATE 模式获取写锁）
        # 先检查优惠券信息
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).with_for_update().first()
        if not coupon:
            raise HTTPException(status_code=404, detail="优惠券不存在")

        if coupon.status != "active":
            raise HTTPException(status_code=409, detail="优惠券未在发行中")

        now = datetime.utcnow()
        if coupon.start_time and coupon.start_time > now:
            raise HTTPException(status_code=409, detail="优惠券尚未开始发行")
        if coupon.end_time and coupon.end_time < now:
            raise HTTPException(status_code=409, detail="优惠券已结束发行")

        # 检查每人限领数量
        user_claimed = db.query(CouponRecord).filter(
            CouponRecord.coupon_id == coupon_id,
            CouponRecord.customer_id == customer_id,
            CouponRecord.binding_id == binding_id,
        ).count()

        if user_claimed >= coupon.per_user_limit:
            raise HTTPException(status_code=429, detail="已超过领取上限")

        # 原子扣减库存（乐观锁核心）
        rows = db.execute(
            db.query(Coupon).filter(
                Coupon.id == coupon_id,
                Coupon.status == "active",
                Coupon.issued_count < Coupon.total_count,
            ).statement.with_only_columns(Coupon.issued_count)
        )
        # 使用 UPDATE 代替直接 SELECT FOR UPDATE（SQLite 兼容）
        result = db.execute(
            Coupon.__table__.update()
            .where(
                Coupon.id == coupon_id,
                Coupon.status == "active",
                Coupon.issued_count < Coupon.total_count,
            )
            .values(issued_count=Coupon.issued_count + 1)
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=409, detail="优惠券已领完")

        # 生成券码
        code = CouponService._generate_code()

        # 计算过期时间
        expires_at = now + timedelta(days=coupon.valid_days)

        # 创建领取记录
        record = CouponRecord(
            coupon_id=coupon_id,
            customer_id=customer_id,
            merchant_id=coupon.merchant_id,
            binding_id=binding_id,
            code=code,
            status="unused",
            expires_at=expires_at,
            version=0,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_my_coupons(
        db: Session,
        customer_id: int,
    ) -> dict:
        """获取我的所有优惠券（按状态分组）"""
        now = datetime.utcnow()

        records = db.query(CouponRecord, Coupon).join(
            Coupon, CouponRecord.coupon_id == Coupon.id
        ).filter(
            CouponRecord.customer_id == customer_id
        ).all()

        unused = []
        used = []
        expired = []

        for record, coupon in records:
            merchant_name = db.query(WxMerchantBinding).filter(
                WxMerchantBinding.id == record.binding_id
            ).first()
            merchant_name = merchant_name.merchant.name if merchant_name else ""

            record_data = {
                "id": record.id,
                "coupon_id": record.coupon_id,
                "coupon_name": coupon.name,
                "merchant_id": record.merchant_id,
                "merchant_name": merchant_name,
                "code": record.code,
                "status": record.status,
                "issued_at": record.issued_at,
                "used_at": record.used_at,
                "expires_at": record.expires_at,
                "threshold": coupon.threshold,
                "discount_value": coupon.discount_value,
                "coupon_type": coupon.type,
            }

            if record.status == "used":
                used.append(record_data)
            elif record.status == "expired" or record.expires_at < now:
                # 更新过期状态
                if record.status != "expired":
                    record.status = "expired"
                    db.commit()
                record_data["status"] = "expired"
                expired.append(record_data)
            else:
                unused.append(record_data)

        return {"unused": unused, "used": used, "expired": expired}

    @staticmethod
    def get_available_coupons(
        db: Session,
        customer_id: int,
        merchant_id: int,
    ) -> List[dict]:
        """获取当前商户可用的优惠券（未使用且未过期）"""
        now = datetime.utcnow()

        records = db.query(CouponRecord, Coupon).join(
            Coupon, CouponRecord.coupon_id == Coupon.id
        ).filter(
            CouponRecord.customer_id == customer_id,
            CouponRecord.merchant_id == merchant_id,
            CouponRecord.status == "unused",
            CouponRecord.expires_at > now,
        ).all()

        result = []
        for record, coupon in records:
            result.append({
                "id": record.id,
                "coupon_id": record.coupon_id,
                "coupon_name": coupon.name,
                "merchant_id": record.merchant_id,
                "merchant_name": coupon.merchant.name,
                "code": record.code,
                "expires_at": record.expires_at,
                "threshold": coupon.threshold,
                "discount_value": coupon.discount_value,
                "type": coupon.type,
            })
        return result

    # ==================== 下单核销校验 ====================

    @staticmethod
    def validate_coupon_for_order(
        db: Session,
        record_id: int,
        binding_id: int,
        merchant_id: int,
        order_amount: float,
    ) -> Tuple[CouponRecord, Coupon, float]:
        """
        校验优惠券是否可用于当前订单
        返回 (record, coupon, discount_amount)
        """
        record = db.query(CouponRecord).filter(CouponRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="优惠券记录不存在")

        if record.binding_id != binding_id:
            raise HTTPException(status_code=403, detail="优惠券不属于当前用户")

        if record.merchant_id != merchant_id:
            raise HTTPException(status_code=403, detail="优惠券不属于当前商户")

        if record.status != "unused":
            raise HTTPException(status_code=409, detail="优惠券已使用")

        if record.expires_at < datetime.utcnow():
            raise HTTPException(status_code=409, detail="优惠券已过期")

        coupon = db.query(Coupon).filter(Coupon.id == record.coupon_id).first()
        if not coupon:
            raise HTTPException(status_code=404, detail="优惠券模板不存在")

        # 门槛检查
        if float(coupon.threshold) > 0 and order_amount < float(coupon.threshold):
            raise HTTPException(
                status_code=400,
                detail=f"订单金额未达到优惠券使用门槛（需满{coupon.threshold}元）"
            )

        # 计算折扣金额
        if coupon.type == "cash":
            discount_amount = min(float(coupon.discount_value), order_amount)
        else:  # discount 折扣券
            discount_amount = order_amount * (1 - float(coupon.discount_value) / 100)

        return record, coupon, round(discount_amount, 2)

    @staticmethod
    def redeem_coupon(
        db: Session,
        record_id: int,
        order_id: int,
        expected_version: int,
    ) -> bool:
        """
        核销优惠券（乐观锁 version 字段）
        返回 True 表示成功，False 表示并发冲突
        """
        result = db.execute(
            CouponRecord.__table__.update()
            .where(
                CouponRecord.id == record_id,
                CouponRecord.status == "unused",
                CouponRecord.version == expected_version,
            )
            .values(
                status="used",
                used_at=datetime.utcnow(),
                used_order_id=order_id,
                version=CouponRecord.version + 1,
            )
        )

        if result.rowcount == 0:
            db.rollback()
            return False

        db.commit()
        return True

    @staticmethod
    def restore_coupon(db: Session, record_id: int) -> bool:
        """取消订单时恢复优惠券状态"""
        result = db.execute(
            CouponRecord.__table__.update()
            .where(
                CouponRecord.id == record_id,
                CouponRecord.status == "used",
            )
            .values(
                status="unused",
                used_at=None,
                used_order_id=None,
                version=CouponRecord.version + 1,
            )
        )
        if result.rowcount == 0:
            return False
        db.commit()
        return True

    # ==================== 核销明细 ====================

    @staticmethod
    def get_coupon_records(
        db: Session,
        coupon_id: int,
        merchant_id: int,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[CouponRecord], int]:
        """获取某优惠券的核销明细"""
        coupon = CouponService.get_coupon_by_id(db, coupon_id, merchant_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="优惠券不存在")

        query = db.query(CouponRecord).filter(CouponRecord.coupon_id == coupon_id)
        total = query.count()
        offset = (page - 1) * limit
        records = query.order_by(CouponRecord.issued_at.desc()).offset(offset).limit(limit).all()

        return records, total

    # ==================== 定时任务 ====================

    @staticmethod
    def expire_old_coupons(db: Session) -> int:
        """将过期未使用的优惠券标记为 expired"""
        now = datetime.utcnow()
        result = db.execute(
            CouponRecord.__table__.update()
            .where(
                CouponRecord.status == "unused",
                CouponRecord.expires_at < now,
            )
            .values(status="expired")
        )
        db.commit()
        return result.rowcount
