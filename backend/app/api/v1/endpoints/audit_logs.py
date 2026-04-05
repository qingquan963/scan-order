"""
Phase 3A - Audit Logs Endpoints
/api/v1/audit-logs/*
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app.database import get_db
from app.schemas.audit_log import AuditLogResponse, AuditLogListResponse
from app.services.audit_service import AuditService
from app.models.platform_admin import PlatformAdmin
from app.models.merchant_user import MerchantUser
from app.api.v1.endpoints.platform_admin import get_current_platform_admin

router = APIRouter()


def get_current_merchant_user(request: Request, db: Session = Depends(get_db)) -> MerchantUser:
    """验证当前商户用户"""
    token = request.cookies.get("merchant_user_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="未认证")
    from app.utils.auth import verify_token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的令牌")
    user_id = payload.get("sub")
    if not user_id or payload.get("user_type") != "merchant_user":
        raise HTTPException(status_code=401, detail="无效的令牌")
    user = db.query(MerchantUser).filter(MerchantUser.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


@router.get("", summary="查询审计日志")
def list_audit_logs(
    request: Request,
    resource_type: Optional[str] = Query(None, description="资源类型"),
    action: Optional[str] = Query(None, description="操作类型"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user)
):
    """
    商户用户：查询当前商户的审计日志
    """
    logs, total = AuditService.get_logs(
        db=db,
        merchant_id=current_user.merchant_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
    )
    return AuditLogListResponse(
        total=total,
        page=page,
        limit=limit,
        logs=[AuditLogResponse.model_validate(log) for log in logs]
    )


@router.get("/all", summary="查询全平台审计日志（仅平台管理员）")
def list_all_audit_logs(
    request: Request,
    merchant_id: Optional[int] = Query(None, description="商户ID筛选"),
    user_id: Optional[int] = Query(None, description="用户ID筛选"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    action: Optional[str] = Query(None, description="操作类型"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin)
):
    """平台管理员：查询全平台审计日志"""
    logs, total = AuditService.get_logs(
        db=db,
        merchant_id=merchant_id,
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
    )
    return AuditLogListResponse(
        total=total,
        page=page,
        limit=limit,
        logs=[AuditLogResponse.model_validate(log) for log in logs]
    )
