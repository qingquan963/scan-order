from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
import re


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./scan_order.db"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_PUBLIC_URL: Optional[str] = Field(default=None, description="前端公开访问URL，用于生成二维码")

    # Phase 3A: WeChat OAuth
    WX_APP_ID: Optional[str] = Field(default=None, description="微信开放平台 AppID")
    WX_APP_SECRET: Optional[str] = Field(default=None, description="微信开放平台 AppSecret")
    WX_CALLBACK_URL: Optional[str] = Field(default=None, description="微信 OAuth 回调地址")

    # Phase 3A: Cookie settings
    COOKIE_DOMAIN: Optional[str] = Field(default=None, description="Cookie 域名（生产环境设置）")
    COOKIE_SECURE: bool = Field(default=False, description="Cookie Secure 标志（HTTPS 环境设为 True）")
    COOKIE_HTTPONLY: bool = Field(default=True, description="Cookie HttpOnly 标志（始终 True）")
    COOKIE_SAMESITE: str = Field(default="lax", description="Cookie SameSite 策略")

    # Phase Kitchen: 后厨屏 PIN 码配置
    KITCHEN_PIN: str = Field(default="1234", description="后厨屏4位PIN码")
    KITCHEN_TOKEN_TTL: int = Field(default=28800, description="后厨访问令牌有效期（秒），默认8小时")

    @field_validator("FRONTEND_PUBLIC_URL", mode="before")
    @classmethod
    def validate_frontend_url(cls, v):
        if v is None or v == "":
            return None
        # Must be a valid URL format
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$", re.IGNORECASE)
        if not url_pattern.match(v):
            raise ValueError(f"FRONTEND_PUBLIC_URL '{v}' is not a valid URL")
        return v


class Config:
    env_file = ".env"
