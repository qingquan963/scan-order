"""
FastAPI 依赖：租户上下文（Phase 2）
"""

from fastapi import Depends, HTTPException, Request
from middleware.tenant_resolver import TenantState


def get_tenant(request: Request) -> TenantState:
    """
    FastAPI 依赖：从 request.state.tenant 获取当前租户。
    用于需要认证的 API 端点。

    使用示例：
        @router.get("/items")
        async def list_items(tenant: TenantState = Depends(get_tenant)):
            ...
    """
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return tenant
