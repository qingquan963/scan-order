"""
Phase 3A - WeChat OAuth Endpoints
/api/v1/wx-auth/*
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.wx_auth import (
    WxAuthStateResponse, WxCallbackRequest, WxTokenResponse,
    WxRefreshRequest, WxAccessTokenResponse
)
from app.services.wx_auth_service import WxAuthService
from app.services.audit_service import AuditService
from app.models.wx_auth import WxAuthState
from app.models.merchant_user import MerchantUser
from app.models.merchant import Merchant
from app.config import Settings

settings = Settings()
router = APIRouter()


def _build_wx_callback_url(request: Request) -> str:
    """构建微信回调 URL"""
    if settings.WX_CALLBACK_URL:
        return settings.WX_CALLBACK_URL
    # 开发环境：使用请求的 origin
    return f"{request.base_url}api/v1/wx-auth/callback"


@router.get("/auth-url", summary="获取微信授权 URL")
def get_wx_auth_url(
    request: Request,
    redirect_uri: str = None,
    db: Session = Depends(get_db)
):
    """
    获取微信 OAuth 授权 URL。
    redirect_uri: 可选，回调时携带的redirect_uri
    返回 auth_url 和 state，供前端跳转到微信授权页
    """
    if not settings.WX_APP_ID:
        raise HTTPException(
            status_code=500,
            detail="WeChat OAuth 未配置（WX_APP_ID 未设置）"
        )

    state, expires_at = WxAuthService.create_auth_state(db, redirect_uri=redirect_uri)

    # 回调地址
    callback_url = redirect_uri or _build_wx_callback_url(request)
    auth_url = WxAuthService.build_auth_url(callback_url, state)

    return WxAuthStateResponse(
        auth_url=auth_url,
        state=state,
        expires_in=int((expires_at - datetime.utcnow()).total_seconds())
    )


from datetime import datetime


@router.post("/callback", summary="微信授权回调")
async def wx_callback(
    request: Request,
    callback_data: WxCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    微信授权回调。
    1. 验证 state（10分钟有效期，使用后标记 used_at）
    2. 用 code 换微信 access_token
    3. 查找或提示绑定 merchant_user
    4. 创建 access_token + 30天 refresh_token
    """
    # 验证 state
    auth_state = WxAuthService.verify_and_consume_state(db, callback_data.state)

    # 用 code 换 token
    wx_data = await WxAuthService.exchange_code_for_token(callback_data.code)

    openid = wx_data.get("openid")
    unionid = wx_data.get("unionid")  # 同一主体下才有

    if not openid:
        raise HTTPException(status_code=400, detail="微信授权失败：未获取到 openid")

    # 查找已有的绑定用户
    user = WxAuthService.find_or_create_merchant_user_by_wx(db, openid, unionid)

    if user:
        # 已绑定用户：创建 token
        token_response = WxAuthService.create_tokens_for_user(db, user)

        # 检查商户状态
        merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
        if not merchant or merchant.status != "active":
            raise HTTPException(status_code=403, detail="商户未激活，请联系平台审核")

        AuditService.log(
            db=db,
            action="wx_login_success",
            user_id=user.id,
            user_type="merchant_user",
            merchant_id=user.merchant_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return token_response

    else:
        # 新微信用户，需要绑定商户
        # 返回提示信息，前端引导用户进行商户绑定
        AuditService.log(
            db=db,
            action="wx_login_unbound",
            user_type="wx_user",
            details={"openid": openid, "has_unionid": bool(unionid)},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return {
            "status": "unbound",
            "openid": openid,
            "unionid": unionid,
            "message": "该微信账号尚未绑定商户用户，请先进行商户绑定"
        }


@router.post("/refresh", summary="刷新 Access Token")
def refresh_token(
    request: Request,
    refresh_data: WxRefreshRequest,
    db: Session = Depends(get_db)
):
    """使用 refresh_token 刷新 access_token"""
    result = WxAuthService.refresh_access_token(db, refresh_data.refresh_token)

    AuditService.log(
        db=db,
        action="token_refresh",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return WxAccessTokenResponse(**result)


@router.get("/wx-login-test", summary="模拟微信登录（开发环境）")
def wx_login_test(
    request: Request,
    merchant_user_id: int,
    db: Session = Depends(get_db)
):
    """开发环境：直接用 merchant_user_id 模拟微信登录（不调用微信API）"""
    if settings.WX_APP_ID and settings.WX_APP_ID != "test":
        raise HTTPException(status_code=403, detail="测试接口仅在开发环境可用")

    user = db.query(MerchantUser).filter(MerchantUser.id == merchant_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
    if not merchant or merchant.status != "active":
        raise HTTPException(status_code=403, detail="商户未激活")

    token_response = WxAuthService.create_tokens_for_user(db, user)
    return token_response
