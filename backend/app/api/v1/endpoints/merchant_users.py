"""
Phase 3A - Merchant User Management Endpoints
/api/v1/merchant-users/*
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.merchant_user import (
    MerchantUserCreate, MerchantUserUpdate, MerchantUserResponse, MerchantUserLogin
)
from app.models.merchant_user import MerchantUser
from app.models.merchant import Merchant
from app.services.audit_service import AuditService
from app.utils.auth import verify_password, get_password_hash, create_access_token
from datetime import timedelta
from app.config import Settings

settings = Settings()
router = APIRouter()


def get_current_merchant_user(request: Request, db: Session = Depends(get_db)) -> MerchantUser:
    """验证当前商户用户（从 cookie 或 header）"""
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

    # 检查商户状态
    merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
    if not merchant or merchant.status != "active":
        raise HTTPException(status_code=403, detail="商户未激活或已停用")

    return user


def require_owner(request: Request, db: Session = Depends(get_db)) -> MerchantUser:
    """要求当前用户是 owner 角色"""
    user = get_current_merchant_user(request, db)
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="需要 owner 权限")
    return user


# --- Unified Auth ---

@router.post("/login", summary="商户用户登录（用户名密码）")
def merchant_user_login(
    request: Request,
    login_data: MerchantUserLogin,
    db: Session = Depends(get_db)
):
    """商户用户登录（支持 owner/staff）"""
    # 先查 merchant_users 表
    user = db.query(MerchantUser).filter(
        MerchantUser.username == login_data.username,
        MerchantUser.is_active == 1
    ).first()

    # 再查 merchants 表（向后兼容 Phase 1/2）
    if not user:
        merchant = db.query(Merchant).filter(
            Merchant.username == login_data.username,
            Merchant.status == "active"
        ).first()
        if merchant:
            # 验证密码
            if verify_password(login_data.password, merchant.password_hash):
                # 构造兼容响应
                token = create_access_token(
                    data={
                        "sub": str(merchant.id),
                        "user_type": "merchant",
                        "role": "owner",
                    },
                    expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                )
                AuditService.log(
                    db=db,
                    action="merchant_legacy_login",
                    merchant_id=merchant.id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    "merchant_id": merchant.id,
                    "merchant_name": merchant.name,
                    "merchant_status": merchant.status,
                    "user_id": merchant.id,
                    "username": merchant.username,
                    "role": "owner",
                }

    # merchant_users 表登录
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")

    # 检查商户状态
    merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=403, detail="商户不存在")
    if merchant.status == "pending":
        raise HTTPException(status_code=403, detail="商户待审核，暂时无法登录")
    if merchant.status != "active":
        raise HTTPException(status_code=403, detail="商户状态异常，暂时无法登录")

    # 创建 token
    token = create_access_token(
        data={
            "sub": str(user.id),
            "merchant_id": str(user.merchant_id),
            "user_type": "merchant_user",
            "role": user.role,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    AuditService.log(
        db=db,
        action="merchant_user_login",
        user_id=user.id,
        user_type="merchant_user",
        merchant_id=user.merchant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "merchant_id": user.merchant_id,
        "merchant_name": merchant.name,
        "merchant_status": merchant.status,
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    }


@router.post("/register", summary="注册新商户用户（商户owner）")
def register_merchant_user(
    request: Request,
    user_data: MerchantUserCreate,
    db: Session = Depends(get_db)
):
    """注册新商户用户（仅 owner 角色）"""
    # 检查商户是否存在且状态正常
    merchant = db.query(Merchant).filter(Merchant.id == user_data.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="商户不存在")
    if merchant.status == "pending":
        raise HTTPException(status_code=403, detail="商户待审核，暂时无法添加用户")

    # 检查用户名是否已存在
    if user_data.username:
        existing = db.query(MerchantUser).filter(
            MerchantUser.username == user_data.username
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")

    if not user_data.password:
        raise HTTPException(status_code=400, detail="密码不能为空")

    user = MerchantUser(
        merchant_id=user_data.merchant_id,
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "merchant_id": user.merchant_id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
    }


# --- Merchant User CRUD (owner only) ---

@router.get("", summary="列出商户用户")
def list_merchant_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(require_owner)
):
    """列出当前商户的所有用户（仅 owner）"""
    users = db.query(MerchantUser).filter(
        MerchantUser.merchant_id == current_user.merchant_id
    ).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.put("/{user_id}", summary="更新商户用户")
def update_merchant_user(
    user_id: int,
    request: Request,
    update_data: MerchantUserUpdate,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(require_owner)
):
    """更新商户用户信息（仅 owner）"""
    user = db.query(MerchantUser).filter(
        MerchantUser.id == user_id,
        MerchantUser.merchant_id == current_user.merchant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if update_data.username is not None:
        # 检查用户名冲突
        existing = db.query(MerchantUser).filter(
            MerchantUser.username == update_data.username,
            MerchantUser.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = update_data.username

    if update_data.password:
        user.password_hash = get_password_hash(update_data.password)

    if update_data.role:
        user.role = update_data.role

    if update_data.is_active is not None:
        user.is_active = update_data.is_active

    db.commit()
    return {"message": "更新成功"}


@router.delete("/{user_id}", summary="删除商户用户")
def delete_merchant_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(require_owner)
):
    """删除商户用户（仅 owner，不能删除自己）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    user = db.query(MerchantUser).filter(
        MerchantUser.id == user_id,
        MerchantUser.merchant_id == current_user.merchant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.delete(user)
    db.commit()
    return {"message": "删除成功"}


@router.get("/me", summary="获取当前用户信息")
def get_me(
    request: Request,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user)
):
    """获取当前登录用户信息"""
    merchant = db.query(Merchant).filter(Merchant.id == current_user.merchant_id).first()
    return {
        "id": current_user.id,
        "merchant_id": current_user.merchant_id,
        "merchant_name": merchant.name if merchant else None,
        "merchant_status": merchant.status if merchant else None,
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
