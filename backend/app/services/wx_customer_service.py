"""
WxCustomer Service - Phase 3B
顾客微信登录（Mini-Program OAuth）和绑定管理
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.wx_customer import WxCustomer, WxMerchantBinding
from app.models.merchant import Merchant
from app.utils.auth import create_access_token, verify_token
from app.config import Settings
from app.services.points_service import PointsService

settings = Settings()

# 微信 API URLs
WX_MINI_APP_LOGIN_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WxCustomerService:
    """顾客微信登录服务（对接小程序）"""

    ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 2  # 2小时

    @staticmethod
    async def login_with_code(
        db: Session,
        code: str,
        merchant_id: int,
    ) -> dict:
        """
        顾客微信小程序登录
        1. 用 code 换取 openid
        2. 查找或创建 wx_customers 记录
        3. 查找或创建 wx_merchant_bindings 记录
        4. 生成 JWT token
        """
        # 校验商户是否存在
        merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            raise HTTPException(status_code=404, detail="商户不存在")
        if merchant.status != "active":
            raise HTTPException(status_code=403, detail="商户未激活")

        # 用 code 换取 openid（这里调用微信接口）
        openid = await WxCustomerService._code_to_openid(code)
        if not openid:
            raise HTTPException(status_code=400, detail="微信登录失败：无法获取 openid")

        # 查找或创建顾客
        customer = db.query(WxCustomer).filter(WxCustomer.wx_openid == openid).first()
        if not customer:
            customer = WxCustomer(
                wx_openid=openid,
                wx_nickname=None,
                wx_avatar=None,
            )
            db.add(customer)
            db.flush()

        # 查找或创建绑定
        binding = PointsService.get_or_create_binding(db, customer.id, merchant_id)

        # 生成 JWT token
        access_token = create_access_token(
            data={
                "sub": str(customer.id),
                "binding_id": str(binding.id),
                "merchant_id": str(merchant_id),
                "user_type": "wx_customer",
            },
            expires_delta=timedelta(seconds=WxCustomerService.ACCESS_TOKEN_EXPIRE_SECONDS)
        )

        # 获取积分和等级
        account = PointsService.get_points_account(db, customer.id, merchant_id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": WxCustomerService.ACCESS_TOKEN_EXPIRE_SECONDS,
            "customer_id": customer.id,
            "binding_id": binding.id,
            "merchant_id": merchant_id,
            "merchant_name": merchant.name,
            "points": account["points"],
            "tier_name": account["tier_name"],
        }

    @staticmethod
    async def _code_to_openid(code: str) -> Optional[str]:
        """
        用微信 code 换取 openid
        开发环境：如果未配置 WX_MINI_APP_ID，则使用模拟 openid
        """
        # 开发/测试环境：未配置时使用模拟 openid
        if not settings.WX_MINI_APP_ID or settings.WX_MINI_APP_ID == "test":
            return f"mock_openid_{code[:16]}"

        params = {
            "appid": settings.WX_MINI_APP_ID,
            "secret": settings.WX_MINI_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(WX_MINI_APP_LOGIN_URL, params=params, timeout=10.0)
                data = resp.json()
                if "errcode" in data and data["errcode"] != 0:
                    print(f"[WxCustomer] WeChat API error: {data}")
                    return None
                return data.get("openid")
        except Exception as e:
            print(f"[WxCustomer] HTTP error: {e}")
            return None

    @staticmethod
    def get_customer_me(
        db: Session,
        customer_id: int,
        binding_id: int,
        merchant_id: int,
    ) -> dict:
        """获取当前顾客信息"""
        from app.models.merchant_settings import MerchantSettings

        customer = db.query(WxCustomer).filter(WxCustomer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="顾客不存在")

        merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            raise HTTPException(status_code=404, detail="商户不存在")

        account = PointsService.get_points_account(db, customer_id, merchant_id)

        settings_obj = db.query(MerchantSettings).filter(
            MerchantSettings.merchant_id == merchant_id
        ).first()

        return {
            "customer_id": customer_id,
            "wx_nickname": customer.wx_nickname,
            "wx_avatar": customer.wx_avatar,
            "binding_id": binding_id,
            "merchant_id": merchant_id,
            "merchant_name": merchant.name,
            "points": account["points"],
            "total_points": account["total_points"],
            "visit_count": account["visit_count"],
            "last_visit": account["last_visit"],
            "tier_name": account["tier_name"],
            "tier_threshold": account["tier_threshold"],
            "next_tier_name": account["next_tier_name"],
            "next_tier_threshold": account["next_tier_threshold"],
            "next_tier_points_needed": account["next_tier_points_needed"],
            "points_enabled": settings_obj.points_enabled if settings_obj else True,
            "points_per_yuan": settings_obj.points_per_yuan if settings_obj else 1,
            "points_max_discount_percent": settings_obj.points_max_discount_percent if settings_obj else 50,
        }
