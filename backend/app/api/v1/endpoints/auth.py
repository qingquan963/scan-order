from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, Token
from app.services.auth_service import authenticate_merchant, register_merchant, create_merchant_token

router = APIRouter()


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """商户登录"""
    merchant = authenticate_merchant(db, login_data)
    access_token = create_merchant_token(merchant)
    
    return Token(
        access_token=access_token,
        merchant_id=merchant.id
    )


@router.post("/register", response_model=Token)
def register(register_data: RegisterRequest, db: Session = Depends(get_db)):
    """商户注册"""
    merchant = register_merchant(db, register_data)
    access_token = create_merchant_token(merchant)
    
    return Token(
        access_token=access_token,
        merchant_id=merchant.id
    )