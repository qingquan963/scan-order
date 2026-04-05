from fastapi import APIRouter, Depends
from app.api.v1.endpoints import auth
from app.api.v1.endpoints.categories import router as categories_router
from app.api.v1.endpoints.dishes import router as dishes_router
from app.api.v1.endpoints.tables import router as tables_router
from app.api.v1.endpoints.orders import router as orders_router
from app.api.v1.endpoints.merchant_settings import router as merchant_settings_router
from app.api.v1.endpoints.platform_admin import router as platform_admin_router
from app.api.v1.endpoints.merchant_users import router as merchant_users_router
from app.api.v1.endpoints.wx_auth import router as wx_auth_router
from app.api.v1.endpoints.audit_logs import router as audit_logs_router
from app.api.v1.endpoints.coupons import router as coupons_router
from app.api.v1.endpoints.points_settings import router as points_settings_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.kitchen import router as kitchen_router
from app.dependencies import get_current_merchant
from app.models.merchant import Merchant

router = APIRouter()

# 认证相关路由（公开，无需认证）
router.include_router(auth.router, prefix="/auth", tags=["认证"])

# Phase 3A: 统一商户用户认证
router.include_router(merchant_users_router, prefix="/merchant-users", tags=["商户用户管理"])

# Phase 3A: 微信授权登录
router.include_router(wx_auth_router, prefix="/wx-auth", tags=["微信授权登录"])

# Phase 3A: 平台管理员（平台管理员专属）
router.include_router(platform_admin_router, prefix="/platform-admin", tags=["平台管理"])

# Phase 3A: 审计日志
router.include_router(audit_logs_router, prefix="/audit-logs", tags=["审计日志"])

# 分类管理路由
router.include_router(categories_router, prefix="/categories", tags=["分类管理"])

# 菜品管理路由
router.include_router(dishes_router, prefix="/dishes", tags=["菜品管理"])

# 桌台管理路由
router.include_router(tables_router, prefix="/tables", tags=["桌台管理"])

# 订单管理路由
router.include_router(orders_router, tags=["订单管理"])

# 商户设置路由
router.include_router(merchant_settings_router, tags=["商户设置"])

# Phase 3B: 优惠券管理路由
router.include_router(coupons_router, tags=["优惠券管理"])

# Phase 3B: 积分规则配置路由
router.include_router(points_settings_router, tags=["积分规则"])

# Phase 3C: 报表路由
router.include_router(reports_router, prefix="/reports", tags=["报表管理"])

# Phase Kitchen: 后厨屏路由（独立令牌认证）
router.include_router(kitchen_router, prefix="/kitchen", tags=["后厨屏"])


@router.get("/health")
def health_check():
    """健康检查接口（公开）"""
    return {"status": "ok", "service": "admin"}


@router.get("/me")
def get_current_merchant_info(current_merchant: Merchant = Depends(get_current_merchant)):
    """获取当前商户信息（需认证）"""
    return {
        "id": current_merchant.id,
        "name": current_merchant.name,
        "username": current_merchant.username,
    }


@router.get("/dashboard")
def admin_dashboard(current_merchant: Merchant = Depends(get_current_merchant)):
    """商户后台仪表盘（需认证）"""
    return {
        "merchant_id": current_merchant.id,
        "merchant_name": current_merchant.name,
        "message": "欢迎使用商户后台"
    }
