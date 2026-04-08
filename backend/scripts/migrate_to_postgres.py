"""
从 SQLite 迁移数据到 PostgreSQL（Phase 1 完成迁移）

用法:
    cd backend
    python scripts/migrate_to_postgres.py

逻辑:
    1. 连接源 SQLite 和目标 PostgreSQL
    2. 读取 SQLite 所有业务表数据
    3. 在 PostgreSQL 创建第一个租户（default_tenant）
    4. 将所有现有数据写入 PostgreSQL，tenant_id 指向 default_tenant
    5. 验证行数一致性
"""
import sys
import os
import sqlite3
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import engine as pg_engine, SessionLocal as PgSession
from app.models.tenant import Tenant

# 源 SQLite
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scan_order.db")
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

# 固定第一个租户的 UUID（迁移后数据不可变）
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

# 需要迁移的业务表（order_items 必须在 orders 后迁移）
BUSINESS_TABLES = [
    "merchants",
    "dining_tables",
    "categories",
    "dishes",
    "orders",
    "order_items",
    "platform_admins",
    "merchant_users",
    "audit_logs",
    "coupons",
    "wx_auth_states",
    "wx_refresh_tokens",
    "merchant_tokens",
    "daily_revenue",
    "monthly_revenue",
    "report_corrections",
    "wx_customers",
    "wx_merchant_bindings",
    "coupon_records",
    "coupon_claim_lock",
    "merchant_settings",
]


def get_sqlite_conn():
    return sqlite3.connect(SQLITE_PATH)


def migrate():
    # 1. 创建默认租户
    print("[1/4] 创建默认租户 ...")
    with PgSession() as sess:
        existing = sess.query(Tenant).filter_by(id=DEFAULT_TENANT_ID).first()
        if existing:
            print(f"  默认租户已存在: {existing.slug}")
        else:
            tenant = Tenant(
                id=DEFAULT_TENANT_ID,
                name="默认商户",
                slug="default",
                tier="trial",
                subscription_status="active",
            )
            sess.add(tenant)
            sess.commit()
            print(f"  默认租户已创建: {tenant.slug}")

    # 2. 连接 SQLite，读取所有表数据
    print("[2/4] 从 SQLite 读取数据 ...")
    sqlite_conn = get_sqlite_conn()
    sqlite_conn.row_factory = sqlite3.Row

    table_data = {}
    for table in BUSINESS_TABLES:
        try:
            cur = sqlite_conn.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cur.fetchall()]
            table_data[table] = rows
            print(f"  {table}: {len(rows)} 行")
        except sqlite3.OperationalError:
            print(f"  [SKIP] {table}: 表不存在")

    sqlite_conn.close()

    # 3. 写入 PostgreSQL
    print("[3/4] 写入 PostgreSQL ...")
    with pg_engine.connect() as conn:
        for table in BUSINESS_TABLES:
            rows = table_data.get(table, [])
            if not rows:
                continue

            # 跳过 sqlite_sequence 等系统表
            if table == "sqlite_sequence":
                continue

            # 移除 sqlite 自动维护字段
            cols = [c for c in rows[0].keys() if c not in ("rowid",)]

            # SQLite -> PostgreSQL 类型转换映射
            bool_model_cols = {"is_available"}

            # Phase 1: 提前检查哪些表有 tenant_id 列
            tenant_tables = set()
            with pg_engine.connect() as check_conn:
                result = check_conn.execute(text("""
                    SELECT table_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND column_name = 'tenant_id'
                """)).fetchall()
                tenant_tables = {r[0] for r in result}

            # INSERT 列包含 tenant_id（如果表有此列）
            insert_cols = list(cols)
            if table in tenant_tables:
                insert_cols.append("tenant_id")
            col_list = ", ".join(insert_cols)

            for row in rows:
                values = {c: row[c] for c in cols if c in rows[0].keys()}
                # 所有业务表加上 tenant_id
                if table in tenant_tables:
                    values["tenant_id"] = DEFAULT_TENANT_ID
                # 布尔类型转换: 只对模型定义为 Boolean 的列转换
                for bc in bool_model_cols:
                    if bc in values and values[bc] is not None:
                        values[bc] = bool(values[bc])

                # 构建 INSERT 语句
                placeholders = ", ".join([f":{c}" for c in insert_cols])
                upsert = text(f"""
                    INSERT INTO {table} ({col_list})
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """)
                conn.execute(upsert, values)

            conn.commit()
            print(f"  [OK] {table}: {len(rows)} 行已写入")

    # 4. 验证行数
    print("[4/4] 验证行数 ...")
    sqlite_conn = get_sqlite_conn()
    with pg_engine.connect() as conn:
        all_ok = True
        for table in BUSINESS_TABLES:
            if table == "sqlite_sequence":
                continue
            try:
                sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                continue

            try:
                pg_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
            except Exception:
                pg_count = "?"

            status = "✅" if sqlite_count == pg_count else "⚠️"
            print(f"  {status} {table}: SQLite={sqlite_count}  PostgreSQL={pg_count}")
            if sqlite_count != pg_count:
                all_ok = False

    sqlite_conn.close()

    print()
    if all_ok:
        print("✅ 迁移完成，行数完全一致！")
    else:
        print("⚠️ 迁移完成，但部分表行数不一致，请检查。")


if __name__ == "__main__":
    migrate()
