from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class MerchantSettingsResponse(BaseModel):
    merchant_id: int
    mode: Literal["counter_pay", "credit_pay"] = "counter_pay"
    updated_at: datetime

    class Config:
        from_attributes = True


class MerchantSettingsUpdate(BaseModel):
    mode: Literal["counter_pay", "credit_pay"]
