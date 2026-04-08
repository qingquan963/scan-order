TIER_FEATURES = {
    "trial": {
        "max_dishes": 30,
        "max_tables": 10,
        "max_daily_orders": 200,
        "max_staff": 1,
        "max_merchants": 1,
        "features": ["menu", "tables", "orders"],
    },
    "basic": {
        "max_dishes": 100,
        "max_tables": 30,
        "max_daily_orders": 1000,
        "max_staff": 3,
        "max_merchants": 1,
        "features": ["menu", "tables", "orders", "kitchen", "export"],
    },
    "standard": {
        "max_dishes": None,      # 无限制
        "max_tables": None,
        "max_daily_orders": None,
        "max_staff": 10,
        "max_merchants": 1,
        "features": ["menu", "tables", "orders", "kitchen", "export", "custom_logo", "multi_staff"],
    },
    "enterprise": {
        "max_dishes": None,
        "max_tables": None,
        "max_daily_orders": None,
        "max_staff": None,       # 无限制
        "max_merchants": 3,
        "features": ["menu", "tables", "orders", "kitchen", "export", "custom_logo",
                     "multi_staff", "custom_domain", "open_api", "advanced_analytics", "multi_merchant"],
    },
}

def check_feature(tier: str, feature: str) -> bool:
    """检查某 tier 是否支持某功能"""
    return feature in TIER_FEATURES.get(tier, {}).get("features", [])

def check_limit(tier: str, limit_key: str, current: int) -> bool:
    """检查是否超限（返回 True=超限，False=正常）"""
    limit = TIER_FEATURES.get(tier, {}).get(limit_key)
    if limit is None:
        return False  # 无限制
    return current >= limit
