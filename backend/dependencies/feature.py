"""FastAPI Depends：功能开关检查（在 TenantMiddleware 之后执行）"""
from fastapi import HTTPException, status
from dependencies.tenant import get_tenant
from billing.tiers import check_feature
from fastapi import Depends, Request

async def require_feature(request: Request, feature_key: str) -> bool:
    """
    用法：@router.get("/kitchen", dependencies=[Depends(lambda r: require_feature(r, "kitchen"))])
    在 TenantMiddleware 填充 request.state.tenant 之后执行，所以能拿到 tenant.tier
    """
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_feature(tenant.tier, feature_key):
        raise HTTPException(
            status_code=403,
            detail=f"功能仅限更高套餐，当前：{tenant.tier}"
        )
    return True
