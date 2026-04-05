from fastapi import APIRouter
from app.api.v1.endpoints import health

router = APIRouter()

# 公共路由
router.include_router(health.router, tags=["健康检查"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "scan-order-api"}
