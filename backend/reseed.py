# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models.merchant import Merchant
from app.models.category import Category
from app.models.dish import Dish
from app.models.table import DiningTable as Table
from app.models.order import Order
from app.models.order_item import OrderItem

from app.utils.auth import get_password_hash
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def seed():
    print('Initializing database...')
    init_db()
    
    db = SessionLocal()
    try:
        # Check if merchant exists
        existing = db.query(Merchant).filter(Merchant.username == "admin").first()
        if existing:
            print('Merchant already exists, skipping...')
            return

        # Create merchant
        merchant = Merchant(
            name="演示商户",
            username="admin",
            password_hash=get_password_hash("admin123")
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
        print(f'Merchant created: id={merchant.id}')

        # Create categories
        categories = [
            Category(name="热销套餐", sort_order=5, merchant_id=merchant.id),
            Category(name="凉菜", sort_order=10, merchant_id=merchant.id),
            Category(name="热菜", sort_order=15, merchant_id=merchant.id),
        ]
        for c in categories:
            db.add(c)
        db.commit()
        for c in categories:
            db.refresh(c)
        print(f'Categories created: {[c.id for c in categories]}')

        # Create dishes
        dishes = [
            Dish(name="红烧肉套餐", description="招牌红烧肉配米饭，肥而不腻", price=38.0, category_id=categories[0].id, image_url="", is_available=True, merchant_id=merchant.id),
            Dish(name="糖醋排骨套餐", description="酸甜可口，大人小孩都爱吃", price=42.0, category_id=categories[0].id, image_url="", is_available=True, merchant_id=merchant.id),
            Dish(name="拍黄瓜", description="清爽开胃，夏季必点", price=18.0, category_id=categories[1].id, image_url="", is_available=True, merchant_id=merchant.id),
            Dish(name="凉拌西红柿", description="酸甜适中，简单美味", price=15.0, category_id=categories[1].id, image_url="", is_available=True, merchant_id=merchant.id),
        ]
        for d in dishes:
            db.add(d)
        db.commit()
        for d in dishes:
            db.refresh(d)
        print(f'Dishes created: {[d.id for d in dishes]}')

        # Create tables
        tables = [
            Table(code="A01", name="A区01桌", capacity=4, status="available", merchant_id=merchant.id),
            Table(code="A02", name="A区02桌", capacity=4, status="available", merchant_id=merchant.id),
            Table(code="B01", name="B区01桌", capacity=6, status="available", merchant_id=merchant.id),
            Table(code="VIP1", name="VIP包厢1", capacity=10, status="available", merchant_id=merchant.id),
        ]
        for t in tables:
            db.add(t)
        db.commit()
        for t in tables:
            db.refresh(t)
        print(f'Tables created: {[t.id for t in tables]}')

        print('Seed completed successfully!')
        print(f'  Admin login: admin / admin123')

    except Exception as e:
        db.rollback()
        print(f'Error: {e}')
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
