"""
租户解析中间件
从 auto-master 迁移（2026-04-08）
功能：从 Header/子域名/JWT 解析 tenant_id，并注入 request state
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from auth.jwt_handler import decode_token


class TenantState:
    """租户上下文（挂载到 request.state）"""
    def __init__(self, tenant_id: str, tier: str, role: str, user_id: str):
        self.tenant_id = tenant_id
        self.tier = tier
        self.role = role
        self.user_id = user_id


async def resolve_tenant(request: Request) -> TenantState:
    """
    解析优先级：X-Tenant-ID Header > Authorization JWT > 公开端点
    公开端点（/auth/*, /health）跳过租户验证
    """
    path = request.url.path

    # 公开端点直接放行
    if path.startswith("/auth/") or path in ("/health", "/docs", "/openapi.json"):
        return None

    # 方式1：X-Tenant-ID Header（管理后台标准用法）
    tenant_header = request.headers.get("X-Tenant-ID")
    if tenant_header:
        # 此时还没验证 JWT，只提取 tenant_id，后续 JWT 中间件再验证
        return TenantState(
            tenant_id=tenant_header,
            tier="unknown",
            role="unknown",
            user_id="unknown",
        )

    # 方式2：从 Authorization JWT 提取
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:])
        if payload:
            return TenantState(
                tenant_id=payload["tenant_id"],
                tier=payload.get("tier", "free"),
                role=payload.get("role", "admin"),
                user_id=payload["sub"],
            )

    # 无租户信息
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing tenant context. Provide X-Tenant-ID header or valid JWT.",
    )


class TenantMiddleware(BaseHTTPMiddleware):
    """FastAPI 中间件：每个请求自动解析租户并挂载到 request.state.tenant"""
    async def dispatch(self, request: Request, call_next):
        try:
            tenant = await resolve_tenant(request)
            request.state.tenant = tenant
        except HTTPException as e:
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)

        response = await call_next(request)
        return response
