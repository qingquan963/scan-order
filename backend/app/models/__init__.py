# app/models/__init__.py
# 导入顺序关键：先 Merchant（引用 Category），后 Category（引用 Merchant）
# 这样 back_populates 解析时，两个属性都已存在

from app.database import Base

# 先定义不含 FK 依赖的主表
from app.models.merchant import Merchant
from app.models.category import Category

# 再定义有 FK 的从表
from app.models.dish import Dish
from app.models.table import DiningTable
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.merchant_settings import MerchantSettings

# Phase 3A: 多商户用户模型
from app.models.platform_admin import PlatformAdmin
from app.models.merchant_user import MerchantUser
from app.models.merchant_token import MerchantToken
from app.models.wx_auth import WxAuthState, WxRefreshToken
from app.models.audit_log import AuditLog

# Phase 3C: 报表模型
from app.models.daily_revenue import DailyRevenue
from app.models.monthly_revenue import MonthlyRevenue
from app.models.report_correction import ReportCorrection

# Phase 1: 租户模型
from app.models.tenant import Tenant

# 强制 SQLAlchemy 完成所有 mapper + relationship 配置
import sqlalchemy.orm
sqlalchemy.orm.configure_mappers()

__all__ = [
    "Merchant", "Category", "Dish", "DiningTable", "Order", "OrderItem", "MerchantSettings",
    "PlatformAdmin", "MerchantUser", "MerchantToken", "WxAuthState", "WxRefreshToken", "AuditLog",
    "DailyRevenue", "MonthlyRevenue", "ReportCorrection",
    "Tenant"
]
