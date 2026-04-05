"""
Phase 3A - Platform Admin Service
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.platform_admin import PlatformAdmin
from app.schemas.platform_admin import PlatformAdminCreate, PlatformAdminUpdate
from app.utils.auth import verify_password, get_password_hash
from datetime import datetime


class PlatformAdminService:
    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> PlatformAdmin:
        """验证平台管理员登录"""
        admin = db.query(PlatformAdmin).filter(
            PlatformAdmin.username == username,
            PlatformAdmin.is_active == 1
        ).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        if not verify_password(password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        return admin

    @staticmethod
    def get_by_id(db: Session, admin_id: int) -> PlatformAdmin:
        """根据ID获取平台管理员"""
        admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="管理员不存在")
        return admin

    @staticmethod
    def create(db: Session, admin_data: PlatformAdminCreate) -> PlatformAdmin:
        """创建平台管理员"""
        existing = db.query(PlatformAdmin).filter(
            PlatformAdmin.username == admin_data.username
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        admin = PlatformAdmin(
            username=admin_data.username,
            password_hash=get_password_hash(admin_data.password),
            role=admin_data.role,
            is_active=1
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin

    @staticmethod
    def update(db: Session, admin_id: int, update_data: PlatformAdminUpdate) -> PlatformAdmin:
        """更新平台管理员"""
        admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="管理员不存在")
        if update_data.password:
            admin.password_hash = get_password_hash(update_data.password)
        if update_data.is_active is not None:
            admin.is_active = update_data.is_active
        if update_data.role:
            admin.role = update_data.role
        admin.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(admin)
        return admin

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 50) -> list[PlatformAdmin]:
        """列出所有平台管理员"""
        return db.query(PlatformAdmin).offset(skip).limit(limit).all()

    @staticmethod
    def delete(db: Session, admin_id: int) -> None:
        """删除平台管理员"""
        admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="管理员不存在")
        db.delete(admin)
        db.commit()
