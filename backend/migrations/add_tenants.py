"""
Phase 1 迁移脚本：创建 tenants 表并为所有业务表添加 tenant_id 列

用法（云服务器上执行）:
    cd /opt/scan-order/backend
    export DATABASE_URL=postgresql://scanorder:scanorder@localhost:5432/scanorder
    python -m migrations.add_tenants

逻辑:
    1. 创建 tenants 表
    2. 创建所有业务表（从 SQLite 迁移后 PostgreSQL 为空）
    3. 为业务表添加 tenant_id 列
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, Base
from app.models.tenant import Tenant          # noqa: F401 — 触发 model 注册
from app.models import *                     # noqa: F401 — 触发所有 model 注册

# 补充：其他已存在但未在 __init__.py 导入的模型
try:
    from app.models.coupon import Coupon, CouponRecord, CouponClaimLock  # noqa: F401
    from app.models.wx_customer import WxCustomer, WxMerchantBinding     # noqa: F401
except ImportError:
    pass  # 可能不存在，跳过


def upgrade():
    """创建 tenants + 业务表 + tenant_id 列"""
    with engine.connect() as conn:
        # 1. 创建 tenants 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tenants (
                id          VARCHAR(36) PRIMARY KEY,
                name        VARCHAR(100)    NOT NULL,
                slug        VARCHAR(50)     UNIQUE NOT NULL,
                tier        VARCHAR(20)     DEFAULT 'trial',
                subscription_status VARCHAR(20) DEFAULT 'active',
                subscription_expires_at TIMESTAMP,
                created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("[OK] tenants table created")

        # 2. 创建所有业务表（从 SQLAlchemy models）
        # 这是必要的，因为 PostgreSQL 初始为空，tables 尚未存在
        Base.metadata.create_all(bind=engine)
        conn.commit()
        print("[OK] All business tables created from models")

        # 3. 为业务表添加 tenant_id 列
        # 从 information_schema 获取所有用户表
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
        """))
        existing_tables = [row[0] for row in result.fetchall()]
        print(f"[INFO] Tables in DB: {existing_tables}")

        # 需要添加 tenant_id 的表（必须已创建）
        tenant_cols = {
            "merchants": "merchants",
            "dining_tables": "tables",
            "categories": "categories",
            "dishes": "dishes",
            "orders": "orders",
            "order_items": "order_items",
            "merchant_users": "staff_users",
        }

        for model_name, col_name in tenant_cols.items():
            table = model_name  # actual table name
            if table not in existing_tables:
                print(f"[SKIP] {table}: not found")
                continue

            try:
                # 检查列是否已存在
                col_check = conn.execute(text(f"""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = 'tenant_id'
                """)).fetchone()

                if col_check:
                    print(f"[SKIP] {table}.tenant_id already exists")
                    continue

                # PostgreSQL 9.6+: ADD COLUMN IF NOT EXISTS
                conn.execute(text(f"""
                    ALTER TABLE {table}
                    ADD COLUMN tenant_id VARCHAR(36)
                    REFERENCES tenants(id)
                    NOT NULL
                    DEFAULT '00000000-0000-0000-0000-000000000001'
                """))
                conn.commit()
                print(f"[OK] {table}.tenant_id column added")
            except Exception as e:
                conn.rollback()
                err = str(e)
                if "duplicate" in err.lower() or "23505" in err:
                    print(f"[SKIP] {table}.tenant_id already exists")
                else:
                    print(f"[WARN] {table}: {e}")


def downgrade():
    """回滚（仅开发环境）"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """))
        tables = [r[0] for r in result.fetchall()]

        for table in reversed(tables):
            if table == "tenants":
                continue
            try:
                conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id"))
                conn.commit()
                print(f"[OK] {table}.tenant_id dropped")
            except Exception as e:
                conn.rollback()
                print(f"[WARN] {table}: {e}")

        conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        conn.commit()
        print("[OK] tenants table dropped")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 1 tenant migration")
    parser.add_argument("--downgrade", action="store_true", help="Run downgrade")
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()
        print("\nMigration complete. Run: python scripts/migrate_to_postgres.py")
