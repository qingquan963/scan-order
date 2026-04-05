#!/usr/bin/env python3
"""
种子数据脚本
用于创建演示商户和测试数据
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models.merchant import Merchant
from app.utils.auth import get_password_hash


def create_demo_merchant():
    """创建演示商户"""
    db = SessionLocal()
    
    try:
        # 检查是否已存在演示商户
        existing_merchant = db.query(Merchant).filter(Merchant.username == "admin").first()
        if existing_merchant:
            print("演示商户已存在，跳过创建")
            return existing_merchant
        
        # 创建演示商户
        merchant = Merchant(
            name="演示商户",
            username="admin",
            password_hash=get_password_hash("admin123")
        )
        
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
        
        print(f"演示商户创建成功:")
        print(f"  ID: {merchant.id}")
        print(f"  用户名: {merchant.username}")
        print(f"  密码: admin123")
        print(f"  商户名: {merchant.name}")
        
        return merchant
        
    except Exception as e:
        db.rollback()
        print(f"创建演示商户失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("初始化数据库...")
    init_db()
    
    print("创建演示商户...")
    merchant = create_demo_merchant()
    
    print("种子数据创建完成！")