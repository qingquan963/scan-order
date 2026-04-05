"""
Phase 3A - Dependency Injection for Authentication

支持两种认证方式：
1. 商户直接认证（Phase 1/2 兼容）：Authorization: Bearer <merchant_token>
2. 商户用户认证（Phase 3A）：Authorization: Bearer <user_token> 或 merchant_user_token cookie
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.merchant import Merchant
from app.models.merchant_user import MerchantUser
from app.utils.auth import verify_token

security = HTTPBearer(auto_error=False)


def get_current_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Merchant:
    """
    JWT验证依赖（Phase 1/2 兼容）：验证商户直接登录的 token
    先查 merchant_users 表（Phase 3A 用户），再查 merchants 表（Phase 1/2 兼容）
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_type = payload.get("user_type", "merchant")

    if user_type == "merchant_user":
        # Phase 3A: 商户用户 token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="无效的令牌")
        user = db.query(MerchantUser).filter(MerchantUser.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="用户不存在或已禁用")
        # 返回关联的 Merchant
        merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
        if not merchant:
            raise HTTPException(status_code=401, detail="商户不存在")
        if merchant.status != "active":
            raise HTTPException(status_code=403, detail="商户未激活")
        return merchant

    else:
        # Phase 1/2: 商户直接 token
        merchant_id = payload.get("sub")
        if merchant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
        merchant = db.query(Merchant).filter(Merchant.id == int(merchant_id)).first()
        if merchant is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="商户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if merchant.status != "active":
            raise HTTPException(status_code=403, detail="商户未激活或已停用")
        return merchant


def get_current_merchant_optional(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Merchant | None:
    """可选的JWT验证：token存在则验证，不存在也返回None"""
    if credentials is None:
        return None
    try:
        return get_current_merchant(credentials, db)
    except HTTPException:
        return None


def get_current_merchant_user(
    request: Request,
    db: Session = Depends(get_db)
) -> MerchantUser:
    """
    Phase 3A: 商户用户认证（支持 Bearer token 或 cookie）
    优先从 cookie 获取 merchant_user_token
    """
    token = request.cookies.get("merchant_user_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="未认证")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的令牌")

    user_type = payload.get("user_type")
    if user_type != "merchant_user":
        raise HTTPException(status_code=401, detail="无效的令牌类型")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的令牌")

    user = db.query(MerchantUser).filter(MerchantUser.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    # 检查商户状态
    merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="商户不存在")
    if merchant.status != "active":
        raise HTTPException(status_code=403, detail="商户未激活")

    return user


def get_wx_customer(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Phase 3B: 微信顾客认证
    从 JWT token 中解析 customer_id, binding_id, merchant_id
    """
    token = request.cookies.get("wx_customer_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="未认证，请先登录")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的令牌")

    user_type = payload.get("user_type")
    if user_type != "wx_customer":
        raise HTTPException(status_code=401, detail="无效的令牌类型")

    customer_id = payload.get("sub")
    binding_id = payload.get("binding_id")
    merchant_id = payload.get("merchant_id")

    if not customer_id or not binding_id or not merchant_id:
        raise HTTPException(status_code=401, detail="无效的令牌")

    # 验证绑定关系仍然有效
    from app.models.wx_customer import WxMerchantBinding
    binding = db.query(WxMerchantBinding).filter(
        WxMerchantBinding.id == int(binding_id),
        WxMerchantBinding.customer_id == int(customer_id),
    ).first()
    if not binding:
        raise HTTPException(status_code=401, detail="绑定关系不存在")

    return {
        "customer_id": int(customer_id),
        "binding_id": int(binding_id),
        "merchant_id": int(merchant_id),
    }
