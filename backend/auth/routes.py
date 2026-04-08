"""
认证路由（Phase 2: JWT + 租户）
POST /api/v1/auth/register — 商户注册（创建租户+商户+用户）
POST /api/v1/auth/login  — 商户登录（JWT token pair）
"""

import uuid
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from auth.jwt_handler import create_token_pair, verify_password, hash_password
from app.database import get_db
from app.models.tenant import Tenant
from app.models.merchant import Merchant
from app.models.merchant_user import MerchantUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _make_slug(name: str) -> str:
    """从名称生成 URL-safe slug"""
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fa5]", "", name.lower())
    slug = slug[:30] or "merchant"
    # 确保唯一（加随机后缀）
    return f"{slug}-{uuid.uuid4().hex[:6]}"


class RegisterRequest(BaseModel):
    """注册请求：email/username 作为登录名 + password + merchant_name"""
    email: str = Field(..., min_length=3, max_length=100)  # 实际存 merchant_users.username
    password: str = Field(..., min_length=6, max_length=100)
    merchant_name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    """登录请求"""
    email: str = Field(..., min_length=1, max_length=100)  # merchant_users.username
    password: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    """统一 Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册新商户：
    1. 检查 username 是否已存在
    2. 创建 Tenant(id, name, slug, tier="trial")
    3. 创建 Merchant (关联 tenant)
    4. 创建 MerchantUser (owner, 关联 merchant + tenant)
    5. 返回 JWT token pair（含 tenant_id, role）
    """
    # 1. 检查 username 是否已存在
    existing = db.query(MerchantUser).filter(
        MerchantUser.username == req.email
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # 2. 创建 Tenant
    tenant_id = str(uuid.uuid4())
    tenant = Tenant(
        id=tenant_id,
        name=req.merchant_name,
        slug=_make_slug(req.merchant_name),
        tier="trial",
        subscription_status="active",
    )
    db.add(tenant)

    # 3. 创建 Merchant（关联 tenant）
    pwd_hash, salt = hash_password(req.password)
    merchant = Merchant(
        tenant_id=tenant_id,
        name=req.merchant_name,
        username=req.email,
        password_hash=f"{pwd_hash}:{salt}",  # 存储为 hash:salt 格式
        status="active",
    )
    db.add(merchant)
    db.flush()  # 获取 merchant.id

    # 4. 创建 MerchantUser (owner)
    user = MerchantUser(
        merchant_id=merchant.id,
        tenant_id=tenant_id,
        username=req.email,
        password_hash=f"{pwd_hash}:{salt}",
        role="owner",
        is_active=1,
    )
    db.add(user)
    db.commit()

    # 5. 返回 JWT token pair
    tokens = create_token_pair(
        user_id=str(user.id),
        tenant_id=tenant_id,
        tier="trial",
        role="owner",
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """商户登录：
    1. 查找 MerchantUser（by username）
    2. verify_password
    3. 返回 JWT token pair（含 tenant_id, role）
    """
    # 1. 查找用户
    user = db.query(MerchantUser).filter(
        MerchantUser.username == req.email,
        MerchantUser.is_active == 1,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # 2. 验证密码（password_hash 格式为 hash:salt）
    try:
        stored_hash, stored_salt = user.password_hash.split(":")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(req.password, stored_hash, stored_salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # 3. 获取 tenant 和 tier
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    tier = tenant.tier if tenant else "trial"

    # 4. 返回 JWT token pair
    tokens = create_token_pair(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        tier=tier,
        role=user.role,
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
    )
