"""
Phase Kitchen 数据库迁移脚本
运行命令: cd backend && python -m scripts.migrate_phase_kitchen

本脚本执行以下迁移:
1. orders 表新增 kitchen_status 字段 (DEFAULT NULL)
2. order_items 表新增 is_done 字段 (DEFAULT 0)
3. orders 表确保 updated_at 字段存在
4. 创建数据库索引以提升查询性能
"""
import sys
import os

# 确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine


def upgrade():
    """执行迁移"""
    print("[MIGRATION] 开始 Phase Kitchen 迁移...")

    with engine.begin() as conn:
        # 1. orders 表新增 kitchen_status
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN kitchen_status VARCHAR(20) DEFAULT NULL"))
            print("[OK] orders.kitchen_status 已添加")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] orders.kitchen_status 已存在，跳过")
            else:
                print(f"[WARN] orders.kitchen_status: {e}")

        # 2. order_items 表新增 is_done
        try:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN is_done INTEGER DEFAULT 0 NOT NULL"))
            print("[OK] order_items.is_done 已添加")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] order_items.is_done 已存在，跳过")
            else:
                print(f"[WARN] order_items.is_done: {e}")

        # 3. orders 表新增 updated_at（如果不存在）
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            print("[OK] orders.updated_at 已添加")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] orders.updated_at 已存在，跳过")
            else:
                print(f"[WARN] orders.updated_at: {e}")

        # 4. 创建索引
        indexes = [
            ("idx_orders_kitchen_status", "CREATE INDEX idx_orders_kitchen_status ON orders(kitchen_status)"),
            ("idx_orders_created_at", "CREATE INDEX idx_orders_created_at ON orders(created_at)"),
            ("idx_order_items_is_done", "CREATE INDEX idx_order_items_is_done ON order_items(is_done)"),
            ("idx_order_items_order_id", "CREATE INDEX idx_order_items_order_id ON order_items(order_id)"),
        ]

        for idx_name, idx_sql in indexes:
            try:
                conn.execute(text(f"CREATE INDEX {idx_name} ON orders(kitchen_status)" if "orders" in idx_sql else f"CREATE INDEX {idx_name} ON order_items(is_done)" if "is_done" in idx_sql else idx_sql.replace("CREATE INDEX idx_orders_kitchen_status ON", "CREATE INDEX IF NOT EXISTS idx_orders_kitchen_status ON")))
                print(f"[OK] 索引 {idx_name} 已创建")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"[SKIP] 索引 {idx_name} 已存在，跳过")
                else:
                    # 尝试用 IF NOT EXISTS
                    try:
                        idx_sql_safe = idx_sql.replace(
                            "CREATE INDEX idx_orders_kitchen_status",
                            "CREATE INDEX IF NOT EXISTS idx_orders_kitchen_status"
                        ).replace(
                            "CREATE INDEX idx_orders_created_at",
                            "CREATE INDEX IF NOT EXISTS idx_orders_created_at"
                        ).replace(
                            "CREATE INDEX idx_order_items_is_done",
                            "CREATE INDEX IF NOT EXISTS idx_order_items_is_done"
                        ).replace(
                            "CREATE INDEX idx_order_items_order_id",
                            "CREATE INDEX IF NOT EXISTS idx_order_items_order_id"
                        )
                        conn.execute(text(idx_sql_safe))
                        print(f"[OK] 索引 {idx_name} 已创建")
                    except Exception as e2:
                        if "already exists" in str(e2).lower():
                            print(f"[SKIP] 索引 {idx_name} 已存在，跳过")
                        else:
                            print(f"[WARN] 索引 {idx_name}: {e2}")

    print("[MIGRATION] Phase Kitchen 迁移完成 OK")


def downgrade():
    """回滚迁移"""
    print("[MIGRATION] 开始回滚 Phase Kitchen 迁移...")

    with engine.begin() as conn:
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_orders_kitchen_status"))
            print("[OK] idx_orders_kitchen_status 已删除")
        except Exception as e:
            print(f"[WARN] idx_orders_kitchen_status: {e}")

        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_order_items_is_done"))
            print("[OK] idx_order_items_is_done 已删除")
        except Exception as e:
            print(f"[WARN] idx_order_items_is_done: {e}")

        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_order_items_order_id"))
            print("[OK] idx_order_items_order_id 已删除")
        except Exception as e:
            print(f"[WARN] idx_order_items_order_id: {e}")

        # 注意: SQLite 不支持 DROP COLUMN，字段保留
        print("[INFO] 字段 kitchen_status / is_done 在 SQLite 中无法删除（需重建表）")

    print("[MIGRATION] 回滚完成（字段可能残留）")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--downgrade", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()
