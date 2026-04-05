from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_merchant
from app.models.merchant import Merchant
from app.models.merchant_settings import MerchantSettings
from app.schemas.merchant_settings import MerchantSettingsResponse, MerchantSettingsUpdate

router = APIRouter()


@router.get("/settings", response_model=MerchantSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取商户设置"""
    settings = db.query(MerchantSettings).filter(
        MerchantSettings.merchant_id == current_merchant.id
    ).first()

    if not settings:
        # 如果没有设置记录，创建一个默认的
        settings = MerchantSettings(
            merchant_id=current_merchant.id,
            mode="counter_pay"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/settings", response_model=MerchantSettingsResponse)
def update_settings(
    settings_update: MerchantSettingsUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """更新商户设置"""
    # Phase 2: 校验 mode 值
    valid_modes = ("counter_pay", "credit_pay")
    if settings_update.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"无效的支付模式: {settings_update.mode}，必须是 {valid_modes}")
    
    settings = db.query(MerchantSettings).filter(
        MerchantSettings.merchant_id == current_merchant.id
    ).first()

    if not settings:
        settings = MerchantSettings(
            merchant_id=current_merchant.id,
            mode=settings_update.mode
        )
        db.add(settings)
    else:
        settings.mode = settings_update.mode

    db.commit()
    db.refresh(settings)
    return settings
