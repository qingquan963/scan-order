"""
Admin Points Settings Endpoint - Phase 3B
/api/v1/admin/merchant/settings/points
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_merchant
from app.models.merchant import Merchant
from app.models.merchant_settings import MerchantSettings
from app.schemas.points import PointsSettingsUpdate, PointsSettingsResponse

router = APIRouter()


@router.get("/merchant/settings/points", response_model=PointsSettingsResponse)
def get_points_settings(
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """获取积分规则配置"""
    settings = db.query(MerchantSettings).filter(
        MerchantSettings.merchant_id == current_merchant.id
    ).first()

    if not settings:
        # 返回默认值
        return PointsSettingsResponse(
            points_enabled=1,
            points_per_yuan=1,
            points_max_discount_percent=50,
        )

    return PointsSettingsResponse(
        points_enabled=settings.points_enabled or 1,
        points_per_yuan=settings.points_per_yuan or 1,
        points_max_discount_percent=settings.points_max_discount_percent or 50,
    )


@router.put("/merchant/settings/points", response_model=PointsSettingsResponse)
def update_points_settings(
    settings_update: PointsSettingsUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """修改积分规则配置（需 owner 角色）"""
    settings = db.query(MerchantSettings).filter(
        MerchantSettings.merchant_id == current_merchant.id
    ).first()

    if not settings:
        # 自动创建设置记录
        settings = MerchantSettings(
            merchant_id=current_merchant.id,
            mode="counter_pay",
            points_enabled=settings_update.points_enabled if settings_update.points_enabled is not None else 1,
            points_per_yuan=settings_update.points_per_yuan if settings_update.points_per_yuan is not None else 1,
            points_max_discount_percent=settings_update.points_max_discount_percent if settings_update.points_max_discount_percent is not None else 50,
        )
        db.add(settings)
    else:
        if settings_update.points_enabled is not None:
            settings.points_enabled = settings_update.points_enabled
        if settings_update.points_per_yuan is not None:
            if settings_update.points_per_yuan < 1 or settings_update.points_per_yuan > 10:
                raise HTTPException(
                    status_code=400,
                    detail="points_per_yuan 建议范围 1~10"
                )
            settings.points_per_yuan = settings_update.points_per_yuan
        if settings_update.points_max_discount_percent is not None:
            if settings_update.points_max_discount_percent < 0 or settings_update.points_max_discount_percent > 100:
                raise HTTPException(
                    status_code=400,
                    detail="points_max_discount_percent 必须在 0~100 之间"
                )
            settings.points_max_discount_percent = settings_update.points_max_discount_percent

    db.commit()
    db.refresh(settings)

    return PointsSettingsResponse(
        points_enabled=settings.points_enabled or 1,
        points_per_yuan=settings.points_per_yuan or 1,
        points_max_discount_percent=settings.points_max_discount_percent or 50,
    )
