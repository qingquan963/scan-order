from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.auth import verify_token
from app.database import get_db
from app.models.merchant import Merchant
from sqlalchemy.orm import Session

security = HTTPBearer()


async def get_current_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Merchant:
    """获取当前认证的商户"""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    merchant_id = payload.get("sub")
    if not merchant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    merchant = db.query(Merchant).filter(Merchant.id == int(merchant_id)).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="商户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return merchant