"""
Phase 3A - WeChat OAuth Service
"""
import secrets
import hashlib
import httpx
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.wx_auth import WxAuthState, WxRefreshToken
from app.models.merchant_user import MerchantUser
from app.models.merchant import Merchant
from app.schemas.wx_auth import WxTokenResponse
from app.utils.auth import create_access_token
from app.config import Settings

settings = Settings()

# WeChat OAuth URLs
WX_AUTHORIZE_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
WX_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WX_USER_INFO_URL = "https://api.weixin.qq.com/sns/userinfo"


class WxAuthService:
    # Token 有效期（秒）
    ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 2  # 2 hours
    REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 30  # 30 days
    STATE_EXPIRE_SECONDS = 60 * 10  # 10 minutes

    @staticmethod
    def generate_state() -> str:
        """生成安全的 state 参数: secrets.token_urlsafe(32) + timestamp"""
        random_part = secrets.token_urlsafe(32)
        timestamp = int(datetime.utcnow().timestamp())
        return f"{random_part}_{timestamp}"

    @staticmethod
    def parse_state(state: str) -> Tuple[str, int]:
        """解析 state，返回 (random_part, timestamp)"""
        parts = state.rsplit("_", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="无效的 state 格式")
        random_part = parts[0]
        try:
            timestamp = int(parts[1])
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的 state 时间戳")
        return random_part, timestamp

    @staticmethod
    def is_state_expired(timestamp: int) -> bool:
        """检查 state 是否过期（10分钟）"""
        created = datetime.fromtimestamp(timestamp)
        now = datetime.utcnow()
        return (now - created).total_seconds() > WxAuthService.STATE_EXPIRE_SECONDS

    @staticmethod
    def hash_token(token: str) -> str:
        """对 token 做哈希（存储时）"""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def build_auth_url(redirect_uri: str, state: str) -> str:
        """构建微信授权 URL"""
        params = {
            "appid": settings.WX_APP_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "state": state,
        }
        query = "&".join(f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items())
        return f"{WX_AUTHORIZE_URL}?{query}#wechat_redirect"

    @staticmethod
    def create_auth_state(db: Session, redirect_uri: str = None) -> Tuple[str, datetime]:
        """创建并存储 auth state"""
        state = WxAuthService.generate_state()
        expires_at = datetime.utcnow() + timedelta(seconds=WxAuthService.STATE_EXPIRE_SECONDS)
        auth_state = WxAuthState(
            state=state,
            redirect_uri=redirect_uri,
            expires_at=expires_at,
        )
        db.add(auth_state)
        db.commit()
        return state, expires_at

    @staticmethod
    def verify_and_consume_state(db: Session, state: str) -> WxAuthState:
        """验证 state 并标记为已使用"""
        auth_state = db.query(WxAuthState).filter(WxAuthState.state == state).first()
        if not auth_state:
            raise HTTPException(status_code=400, detail="无效的 state")
        if auth_state.used_at:
            raise HTTPException(status_code=400, detail="state 已被使用")
        if auth_state.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="state 已过期")
        # 标记为已使用
        auth_state.used_at = datetime.utcnow()
        db.commit()
        return auth_state

    @staticmethod
    async def exchange_code_for_token(code: str) -> dict:
        """用 code 换取微信 access_token"""
        params = {
            "appid": settings.WX_APP_ID,
            "secret": settings.WX_APP_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(WX_ACCESS_TOKEN_URL, params=params, timeout=10.0)
            data = resp.json()
            if "errcode" in data and data["errcode"] != 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"微信授权失败: {data.get('errmsg', 'unknown error')}"
                )
            return data  # {access_token, expires_in, refresh_token, openid, scope, unionid}

    @staticmethod
    def find_or_create_merchant_user_by_wx(
        db: Session, openid: str, unionid: Optional[str], wx_nickname: str = None
    ) -> MerchantUser:
        """根据微信 openid 查找或创建商户用户"""
        # 先尝试通过 openid 查找
        user = db.query(MerchantUser).filter(MerchantUser.wx_openid == openid).first()
        if user:
            # 更新 unionid
            if unionid and not user.wx_unionid:
                user.wx_unionid = unionid
                db.commit()
            return user

        # 找不到用户，返回 None（表示需要绑定商户）
        return None

    @staticmethod
    def create_tokens_for_user(db: Session, user: MerchantUser) -> WxTokenResponse:
        """为商户用户创建 access_token 和 refresh_token"""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=WxAuthService.ACCESS_TOKEN_EXPIRE_SECONDS)

        # Access token (JWT)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "merchant_id": str(user.merchant_id),
                "user_type": "merchant_user",
                "role": user.role,
            },
            expires_delta=timedelta(seconds=WxAuthService.ACCESS_TOKEN_EXPIRE_SECONDS)
        )

        # Refresh token (random)
        refresh_token_str = secrets.token_urlsafe(32)
        refresh_expires_at = now + timedelta(seconds=WxAuthService.REFRESH_TOKEN_EXPIRE_SECONDS)

        # 存储 refresh token
        from app.models.merchant_token import MerchantToken
        rt_record = WxRefreshToken(
            merchant_user_id=user.id,
            refresh_token=refresh_token_str,
            expires_at=refresh_expires_at,
        )
        db.add(rt_record)

        # 也存储 access token hash 用于撤销
        access_hash = WxAuthService.hash_token(access_token)
        token_record = MerchantToken(
            merchant_user_id=user.id,
            token_hash=access_hash,
            token_type="access",
            expires_at=expires_at,
        )
        db.add(token_record)

        db.commit()

        return WxTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            expires_in=WxAuthService.ACCESS_TOKEN_EXPIRE_SECONDS,
            merchant_id=user.merchant_id,
            user_id=user.id,
            user_role=user.role,
        )

    @staticmethod
    def refresh_access_token(db: Session, refresh_token_str: str) -> dict:
        """使用 refresh_token 刷新 access_token"""
        rt = db.query(WxRefreshToken).filter(
            WxRefreshToken.refresh_token == refresh_token_str
        ).first()

        if not rt:
            raise HTTPException(status_code=401, detail="无效的 refresh token")
        if rt.used_at:
            raise HTTPException(status_code=401, detail="refresh token 已使用")
        if rt.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="refresh token 已过期")

        # 标记 refresh token 为已使用（一次性）
        rt.used_at = datetime.utcnow()

        user = db.query(MerchantUser).filter(MerchantUser.id == rt.merchant_user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="用户不存在或已禁用")

        # 检查商户状态
        merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
        if not merchant or merchant.status != "active":
            raise HTTPException(status_code=403, detail="商户未激活")

        # 创建新的 access token
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=WxAuthService.ACCESS_TOKEN_EXPIRE_SECONDS)

        new_access_token = create_access_token(
            data={
                "sub": str(user.id),
                "merchant_id": str(user.merchant_id),
                "user_type": "merchant_user",
                "role": user.role,
            },
            expires_delta=timedelta(seconds=WxAuthService.ACCESS_TOKEN_EXPIRE_SECONDS)
        )

        # 存储新的 access token hash
        from app.models.merchant_token import MerchantToken
        new_hash = WxAuthService.hash_token(new_access_token)
        new_token_record = MerchantToken(
            merchant_user_id=user.id,
            token_hash=new_hash,
            token_type="access",
            expires_at=expires_at,
        )
        db.add(new_token_record)
        db.commit()

        return {
            "access_token": new_access_token,
            "expires_in": WxAuthService.ACCESS_TOKEN_EXPIRE_SECONDS,
        }

    @staticmethod
    def cleanup_expired_states(db: Session) -> int:
        """清理过期的 auth states（定时任务）"""
        expired = db.query(WxAuthState).filter(
            WxAuthState.expires_at < datetime.utcnow(),
            WxAuthState.used_at.is_(None)
        ).delete()
        db.commit()
        return expired
