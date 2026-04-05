"""
Phase 3B Database Migration Script
Coupon System + Points System

Usage:
    python migrate_phase3b.py

Tables created:
    - wx_customers: WeChat customer base info
    - wx_merchant_bindings: Customer x Merchant binding (with points)
    - coupons: Coupon template table
    - coupon_records: Coupon claim/use records
    - coupon_claim_lock: Distributed lock for coupon issuance
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine


def upgrade():
    """Apply Phase 3B schema changes."""
    print("[Phase3B Migration] Starting database migration...")

    with engine.connect() as conn:
        # 1. Create wx_customers table
        print("[Phase3B] Creating wx_customers table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wx_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wx_openid VARCHAR(100) UNIQUE NOT NULL,
                wx_unionid VARCHAR(100),
                wx_nickname VARCHAR(255),
                wx_avatar VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("[Phase3B]   - wx_customers table created")

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wx_customers_openid ON wx_customers(wx_openid)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3B]   - Index warning: {e}")

        # 2. Create wx_merchant_bindings table
        print("[Phase3B] Creating wx_merchant_bindings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wx_merchant_bindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                merchant_id INTEGER NOT NULL,
                points INTEGER DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                visit_count INTEGER DEFAULT 0,
                last_visit TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES wx_customers(id),
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                UNIQUE(customer_id, merchant_id)
            )
        """))
        conn.commit()
        print("[Phase3B]   - wx_merchant_bindings table created")

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bindings_customer ON wx_merchant_bindings(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bindings_merchant ON wx_merchant_bindings(merchant_id)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3B]   - Index warning: {e}")

        # 3. Create coupons table
        print("[Phase3B] Creating coupons table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                type VARCHAR(20) NOT NULL,
                threshold DECIMAL(10,2) DEFAULT 0,
                discount_value DECIMAL(10,2) NOT NULL,
                total_count INTEGER NOT NULL,
                issued_count INTEGER DEFAULT 0,
                per_user_limit INTEGER DEFAULT 1,
                valid_days INTEGER DEFAULT 30,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """))
        conn.commit()
        print("[Phase3B]   - coupons table created")

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_coupons_merchant ON coupons(merchant_id)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3B]   - Index warning: {e}")

        # 4. Create coupon_records table
        print("[Phase3B] Creating coupon_records table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS coupon_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                merchant_id INTEGER NOT NULL,
                binding_id INTEGER NOT NULL,
                code VARCHAR(50) NOT NULL UNIQUE,
                status VARCHAR(20) DEFAULT 'unused',
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                used_order_id INTEGER,
                expires_at TIMESTAMP NOT NULL,
                version INTEGER DEFAULT 0,
                FOREIGN KEY (coupon_id) REFERENCES coupons(id),
                FOREIGN KEY (customer_id) REFERENCES wx_customers(id),
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                FOREIGN KEY (binding_id) REFERENCES wx_merchant_bindings(id),
                UNIQUE(binding_id, used_order_id)
            )
        """))
        conn.commit()
        print("[Phase3B]   - coupon_records table created")

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_coupon_records_customer ON coupon_records(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_coupon_records_merchant ON coupon_records(merchant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_coupon_records_code ON coupon_records(code)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_coupon_records_coupon ON coupon_records(coupon_id)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3B]   - Index warning: {e}")

        # 5. Create coupon_claim_lock table
        print("[Phase3B] Creating coupon_claim_lock table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS coupon_claim_lock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_id INTEGER NOT NULL UNIQUE,
                lock_token VARCHAR(64) NOT NULL UNIQUE,
                acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (coupon_id) REFERENCES coupons(id)
            )
        """))
        conn.commit()
        print("[Phase3B]   - coupon_claim_lock table created")

        # 6. Add fields to merchant_settings
        print("[Phase3B] Adding fields to merchant_settings...")
        try:
            conn.execute(text("ALTER TABLE merchant_settings ADD COLUMN points_enabled INTEGER DEFAULT 1"))
            conn.commit()
            print("[Phase3B]   - merchant_settings.points_enabled added (default: 1)")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - merchant_settings.points_enabled already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        try:
            conn.execute(text("ALTER TABLE merchant_settings ADD COLUMN points_per_yuan INTEGER DEFAULT 1"))
            conn.commit()
            print("[Phase3B]   - merchant_settings.points_per_yuan added (default: 1)")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - merchant_settings.points_per_yuan already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        try:
            conn.execute(text("ALTER TABLE merchant_settings ADD COLUMN points_max_discount_percent INTEGER DEFAULT 50"))
            conn.commit()
            print("[Phase3B]   - merchant_settings.points_max_discount_percent added (default: 50)")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - merchant_settings.points_max_discount_percent already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        # 7. Add fields to orders
        print("[Phase3B] Adding fields to orders...")
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN coupon_discount DECIMAL(10,2) DEFAULT 0"))
            conn.commit()
            print("[Phase3B]   - orders.coupon_discount added (default: 0)")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - orders.coupon_discount already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN points_discount DECIMAL(10,2) DEFAULT 0"))
            conn.commit()
            print("[Phase3B]   - orders.points_discount added (default: 0)")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - orders.points_discount already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN customer_id INTEGER"))
            conn.commit()
            print("[Phase3B]   - orders.customer_id added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - orders.customer_id already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN binding_id INTEGER"))
            conn.commit()
            print("[Phase3B]   - orders.binding_id added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - orders.binding_id already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN coupon_record_id INTEGER"))
            conn.commit()
            print("[Phase3B]   - orders.coupon_record_id added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3B]   - orders.coupon_record_id already exists, skipping")
            else:
                print(f"[Phase3B]   - WARNING: {e}")

        # 8. Create expired coupons cron helper view
        print("[Phase3B] Creating coupon expiration cron helper...")
        conn.execute(text("""
            CREATE VIEW IF NOT EXISTS v_expired_coupons AS
            SELECT cr.id, cr.coupon_id, cr.binding_id, cr.customer_id, cr.status
            FROM coupon_records cr
            WHERE cr.status = 'unused'
              AND cr.expires_at < CURRENT_TIMESTAMP
        """))
        conn.commit()
        print("[Phase3B]   - v_expired_coupons view created")

    print("[Phase3B Migration] Completed successfully!")
    print("")
    print("Summary of changes:")
    print("  - wx_customers: NEW table for WeChat customer base info")
    print("  - wx_merchant_bindings: NEW table (customer x merchant with points)")
    print("  - coupons: NEW table for coupon templates")
    print("  - coupon_records: NEW table for coupon claim/use records")
    print("  - coupon_claim_lock: NEW table for distributed claim lock")
    print("  - merchant_settings: added points_enabled, points_per_yuan, points_max_discount_percent")
    print("  - orders: added coupon_discount, points_discount, customer_id, binding_id, coupon_record_id")


def downgrade():
    """Rollback Phase 3B schema changes (DANGER: data loss)."""
    print("[Phase3B Migration] Rolling back changes...")

    with engine.connect() as conn:
        conn.execute(text("DROP VIEW IF EXISTS v_expired_coupons"))
        conn.execute(text("DROP TABLE IF EXISTS coupon_claim_lock"))
        conn.execute(text("DROP TABLE IF EXISTS coupon_records"))
        conn.execute(text("DROP TABLE IF EXISTS coupons"))
        conn.execute(text("DROP TABLE IF EXISTS wx_merchant_bindings"))
        conn.execute(text("DROP TABLE IF EXISTS wx_customers"))
        conn.commit()
        print("[Phase3B]   - Dropped all Phase 3B tables")

        # Note: SQLite doesn't support DROP COLUMN, so we leave added columns in place
        print("[Phase3B]   - Note: Added columns in orders/merchant_settings retained (SQLite limitation)")

    print("[Phase3B Migration] Rollback completed!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--downgrade":
            confirm = input("Are you sure you want to drop all Phase 3B tables? This will cause data loss! Type 'yes' to confirm: ")
            if confirm == "yes":
                downgrade()
            else:
                print("Aborted.")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python migrate_phase3b.py [--downgrade]")
    else:
        upgrade()
