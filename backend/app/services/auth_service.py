from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.merchant import Merchant
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.auth import verify_password, get_password_hash, create_access_token
from datetime import timedelta
from app.config import Settings

settings = Settings()


def authenticate_merchant(db: Session, login_data: LoginRequest) -> Merchant:
    """验证商户登录"""
    merchant = db.query(Merchant).filter(Merchant.username == login_data.username).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not verify_password(login_data.password, merchant.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    return merchant


def register_merchant(db: Session, register_data: RegisterRequest) -> Merchant:
    """注册新商户"""
    # 检查用户名是否已存在
    existing_merchant = db.query(Merchant).filter(Merchant.username == register_data.username).first()
    if existing_merchant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建新商户
    merchant = Merchant(
        name=register_data.name,
        username=register_data.username,
        password_hash=get_password_hash(register_data.password)
    )
    
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    
    return merchant


def create_merchant_token(merchant: Merchant) -> str:
    """为商户创建JWT token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(merchant.id), "username": merchant.username},
        expires_delta=access_token_expires
    )
    return access_token