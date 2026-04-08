"""
JWT 认证处理模块
从 auto-master 迁移（2026-04-08）
功能：JWT 签发、验证、refresh
"""

import time
import jwt
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

# ─── 配置（从环境变量读取）────────────────────────────────────
JWT_SECRET = "scan-order-saas-2026-change-me-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24       # 24小时
REFRESH_TOKEN_EXPIRE_DAYS = 30


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class TokenPayload(BaseModel):
    sub: str           # user_id
    tenant_id: str     # 租户ID
    tier: str          # free/pro/enterprise
    role: str          # admin/staff/customer
    exp: int


def _make_exp(minutes: int) -> int:
    return int(time.time()) + minutes * 60


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """SHA256 + salt 哈希，返回 (hash, salt)"""
    salt = salt or uuid.uuid4().hex[:16]
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return h, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码"""
    h, _ = hash_password(password, salt)
    return h == hashed


def create_token_pair(
    user_id: str,
    tenant_id: str,
    tier: str = "free",
    role: str = "admin",
) -> TokenPair:
    """生成 access_token + refresh_token 对"""
    now = int(time.time())

    access_payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "tier": tier,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": _make_exp(ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    refresh_payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "refresh",
        "iat": now,
        "exp": _make_exp(REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60),
    }

    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def decode_token(token: str) -> Optional[dict]:
    """解码 JWT，失败返回 None"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(authorization: str = None) -> TokenPayload:
    """
    依赖注入：从 Authorization: Bearer <token> 提取 payload。
    FastAPI: Depends(require_auth)
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise ValueError("Invalid or expired token")
    if payload.get("type") != "access":
        raise ValueError("Not an access token")
    return TokenPayload(**payload)
