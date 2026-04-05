# app/schemas/__init__.py
from app.schemas.auth import Token, LoginRequest, RegisterRequest, UnifiedTokenResponse, MerchantUserTokenResponse
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishToggleResponse
from app.schemas.order import OrderResponse, OrderListResponse, OrderStatusUpdate, TodayStatsResponse, SalesStatsResponse
from app.schemas.table import TableCreate, TableUpdate, TableResponse
from app.schemas.merchant_settings import MerchantSettingsResponse, MerchantSettingsUpdate
from app.schemas.platform_admin import PlatformAdminCreate, PlatformAdminUpdate, PlatformAdminResponse
from app.schemas.merchant_user import MerchantUserCreate, MerchantUserUpdate, MerchantUserResponse, MerchantUserLogin
from app.schemas.wx_auth import WxAuthStateResponse, WxCallbackRequest, WxTokenResponse, WxRefreshRequest, WxAccessTokenResponse
from app.schemas.audit_log import AuditLogResponse, AuditLogListResponse

__all__ = [
    "Token", "LoginRequest", "RegisterRequest", "UnifiedTokenResponse", "MerchantUserTokenResponse",
    "CategoryCreate", "CategoryUpdate", "CategoryResponse",
    "DishCreate", "DishUpdate", "DishResponse", "DishToggleResponse",
    "OrderResponse", "OrderListResponse", "OrderStatusUpdate", "TodayStatsResponse", "SalesStatsResponse",
    "TableCreate", "TableUpdate", "TableResponse",
    "MerchantSettingsResponse", "MerchantSettingsUpdate",
    "PlatformAdminCreate", "PlatformAdminUpdate", "PlatformAdminResponse",
    "MerchantUserCreate", "MerchantUserUpdate", "MerchantUserResponse", "MerchantUserLogin",
    "WxAuthStateResponse", "WxCallbackRequest", "WxTokenResponse", "WxRefreshRequest", "WxAccessTokenResponse",
    "AuditLogResponse", "AuditLogListResponse",
]
