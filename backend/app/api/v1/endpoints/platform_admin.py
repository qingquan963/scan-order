"""
Phase 3A - Platform Admin Endpoints
/api/v1/platform-admin/*
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.platform_admin import (
    PlatformAdminCreate, PlatformAdminUpdate, PlatformAdminResponse
)
from app.services.platform_admin_service import PlatformAdminService
from app.services.audit_service import AuditService
from app.models.platform_admin import PlatformAdmin
from app.models.merchant import Merchant
from app.utils.auth import create_access_token
from datetime import timedelta

router = APIRouter()


def get_current_platform_admin(request: Request, db: Session = Depends(get_db)) -> PlatformAdmin:
    """验证平台管理员身份（从 cookie 或 header）"""
    # 优先从 cookie 获取
    token = request.cookies.get("platform_admin_token")
    if not token:
        # 回退到 Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="未认证")

    from app.utils.auth import verify_token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的令牌")

    admin_id = payload.get("sub")
    if not admin_id or payload.get("user_type") != "platform_admin":
        raise HTTPException(status_code=401, detail="无效的令牌")

    admin = db.query(PlatformAdmin).filter(
        PlatformAdmin.id == int(admin_id),
        PlatformAdmin.is_active == 1
    ).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在或已禁用")

    return admin


# --- Platform Admin Auth ---

@router.post("/auth/login")
def platform_admin_login(
    request: Request,
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    """平台管理员登录"""
    admin = PlatformAdminService.authenticate(db, username, password)
    token = create_access_token(
        data={
            "sub": str(admin.id),
            "user_type": "platform_admin",
            "role": admin.role,
        },
        expires_delta=timedelta(hours=8)
    )

    AuditService.log(
        db=db,
        action="platform_admin_login",
        user_id=admin.id,
        user_type="platform_admin",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    response = {
        "access_token": token,
        "token_type": "bearer",
        "admin_id": admin.id,
        "role": admin.role,
    }
    return response


# --- Merchant Management (Platform Admin) ---

@router.get("/merchants", summary="列出所有商户（含待审核）")
def list_all_merchants(
    request: Request,
    status_filter: str = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin)
):
    """平台管理员：列出所有商户（含待审核状态）"""
    query = db.query(Merchant)
    if status_filter:
        query = query.filter(Merchant.status == status_filter)
    total = query.count()
    merchants = query.order_by(Merchant.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "merchants": [
            {
                "id": m.id,
                "name": m.name,
                "username": m.username,
                "status": m.status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in merchants
        ]
    }


@router.put("/merchants/{merchant_id}/approve", summary="审核通过商户")
def approve_merchant(
    merchant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin)
):
    """平台管理员：审核通过商户"""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="商户不存在")

    if merchant.status == "active":
        return {"message": "商户已经是 active 状态", "status": merchant.status}

    merchant.status = "active"
    db.commit()

    AuditService.log(
        db=db,
        action="merchant_approve",
        user_id=current_admin.id,
        user_type="platform_admin",
        merchant_id=merchant_id,
        resource_type="merchant",
        resource_id=merchant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "商户已审核通过", "status": "active"}


@router.put("/merchants/{merchant_id}/reject", summary="拒绝商户入驻")
def reject_merchant(
    merchant_id: int,
    reason: str = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin)
):
    """平台管理员：拒绝商户入驻"""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="商户不存在")

    merchant.status = "rejected"
    db.commit()

    AuditService.log(
        db=db,
        action="merchant_reject",
        user_id=current_admin.id,
        user_type="platform_admin",
        merchant_id=merchant_id,
        resource_type="merchant",
        resource_id=merchant_id,
        details={"reason": reason} if reason else None,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )

    return {"message": "商户已拒绝", "status": "rejected"}


@router.put("/merchants/{merchant_id}/suspend", summary="暂停商户")
def suspend_merchant(
    merchant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin)
):
    """平台管理员：暂停商户"""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="商户不存在")

    merchant.status = "suspended"
    db.commit()
    return {"message": "商户已暂停", "status": "suspended"}


# --- Platform Admin Management ---

@router.get("/admins", response_model=List[PlatformAdminResponse])
def list_admins(
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin)
):
    """列出所有平台管理员（仅 super_admin）"""
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="需要 super_admin 权限")
    admins = PlatformAdminService.list(db, skip=(page - 1) * limit, limit=limit)
    return admins


@router.post("/admins", response_model=PlatformAdminResponse)
def create_admin(
    admin_data: PlatformAdminCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: PlatformAdmin = Depends(get_current_platform_admin)
):
    """创建平台管理员（仅 super_admin）"""
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="需要 super_admin 权限")
    admin = PlatformAdminService.create(db, admin_data)
    AuditService.log(
        db=db,
        action="platform_admin_create",
        user_id=current_admin.id,
        user_type="platform_admin",
        resource_type="platform_admin",
        resource_id=admin.id,
        ip_address=request.client.host if request.client else None,
    )
    return admin
