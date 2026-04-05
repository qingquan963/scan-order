"""
Phase 3A - Audit Log Service
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def log(
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        user_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        merchant_id: Optional[int] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录审计日志"""
        log_entry = AuditLog(
            user_id=user_id,
            user_type=user_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            merchant_id=merchant_id,
            details=json.dumps(details, ensure_ascii=False) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def log_merchant_access(
        db: Session,
        action: str,
        user_id: int,
        user_type: str,
        merchant_id: int,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录商户数据访问（简化接口）"""
        return AuditService.log(
            db=db,
            action=action,
            user_id=user_id,
            user_type=user_type,
            merchant_id=merchant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def get_logs(
        db: Session,
        merchant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """查询审计日志（支持过滤）"""
        query = db.query(AuditLog)

        if merchant_id is not None:
            query = query.filter(AuditLog.merchant_id == merchant_id)
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        total = query.count()
        logs = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * limit).limit(limit).all()
        return logs, total

    @staticmethod
    def cleanup_old_logs(db: Session, days: int = 90) -> int:
        """清理超过指定天数的日志"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete()
        db.commit()
        return deleted
