"""
Phase 3C Database Migration Script
Reporting System: daily_revenue, monthly_revenue, report_corrections

Usage:
    python migrate_phase3c.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine


def upgrade():
    """Apply Phase 3C schema changes."""
    print("[Phase3C Migration] Starting database migration...")

    with engine.connect() as conn:
        # 1. Create daily_revenue table
        print("[Phase3C] Creating daily_revenue table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_revenue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                stat_date DATE NOT NULL,
                total_orders INTEGER DEFAULT 0,
                total_amount DECIMAL(12,2) DEFAULT 0,
                total_dishes INTEGER DEFAULT 0,
                avg_order_amount DECIMAL(10,2) DEFAULT 0,
                paid_count INTEGER DEFAULT 0,
                cancelled_count INTEGER DEFAULT 0,
                cash_orders INTEGER DEFAULT 0,
                credit_orders INTEGER DEFAULT 0,
                coupon_discount DECIMAL(10,2) DEFAULT 0,
                points_discount DECIMAL(10,2) DEFAULT 0,
                new_customers INTEGER DEFAULT 0,
                returning_customers INTEGER DEFAULT 0,
                is_finalized INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 0,
                UNIQUE(merchant_id, stat_date)
            )
        """))
        conn.commit()
        print("[Phase3C]   - daily_revenue table created")

        # 2. Create index on daily_revenue
        print("[Phase3C] Creating indexes on daily_revenue...")
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_daily_revenue_merchant_date ON daily_revenue(merchant_id, stat_date)"))
            conn.commit()
            print("[Phase3C]   - idx_daily_revenue_merchant_date created")
        except Exception as e:
            print(f"[Phase3C]   - Index warning: {e}")

        # 3. Create monthly_revenue table
        print("[Phase3C] Creating monthly_revenue table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS monthly_revenue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                stat_year INTEGER NOT NULL,
                stat_month INTEGER NOT NULL,
                total_orders INTEGER DEFAULT 0,
                total_amount DECIMAL(12,2) DEFAULT 0,
                total_dishes INTEGER DEFAULT 0,
                avg_order_amount DECIMAL(10,2) DEFAULT 0,
                paid_count INTEGER DEFAULT 0,
                cancelled_count INTEGER DEFAULT 0,
                cash_orders INTEGER DEFAULT 0,
                credit_orders INTEGER DEFAULT 0,
                coupon_discount DECIMAL(10,2) DEFAULT 0,
                points_discount DECIMAL(10,2) DEFAULT 0,
                new_customers INTEGER DEFAULT 0,
                returning_customers INTEGER DEFAULT 0,
                is_finalized INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 0,
                UNIQUE(merchant_id, stat_year, stat_month)
            )
        """))
        conn.commit()
        print("[Phase3C]   - monthly_revenue table created")

        # 4. Create index on monthly_revenue
        print("[Phase3C] Creating indexes on monthly_revenue...")
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_monthly_revenue_merchant_ym ON monthly_revenue(merchant_id, stat_year, stat_month)"))
            conn.commit()
            print("[Phase3C]   - idx_monthly_revenue_merchant_ym created")
        except Exception as e:
            print(f"[Phase3C]   - Index warning: {e}")

        # 5. Create report_corrections table
        print("[Phase3C] Creating report_corrections table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS report_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                report_type VARCHAR(20) NOT NULL,
                stat_date DATE NOT NULL,
                old_total_amount DECIMAL(12,2),
                new_total_amount DECIMAL(12,2),
                corrected_by INTEGER NOT NULL,
                reason TEXT,
                is_undo INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("[Phase3C]   - report_corrections table created")

        # 6. Create index on report_corrections
        print("[Phase3C] Creating indexes on report_corrections...")
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_report_corrections_merchant ON report_corrections(merchant_id, stat_date)"))
            conn.commit()
            print("[Phase3C]   - idx_report_corrections_merchant created")
        except Exception as e:
            print(f"[Phase3C]   - Index warning: {e}")

        # 7. Verify table structures
        print("[Phase3C] Verifying table structures...")
        tables = ["daily_revenue", "monthly_revenue", "report_corrections"]
        for table in tables:
            result = conn.execute(text(f"PRAGMA table_info({table})"))
            cols = [row[1] for row in result]
            print(f"[Phase3C]   - {table}: {len(cols)} columns OK")

    print("[Phase3C Migration] Completed successfully!")
    print("")
    print("Summary of changes:")
    print("  - daily_revenue: NEW table for daily revenue reports")
    print("  - monthly_revenue: NEW table for monthly revenue reports")
    print("  - report_corrections: NEW table for report correction audit trail")
    print("")
    print("Next steps:")
    print("  1. Run: python scripts/backfill_reports.py --help  (optional, to backfill historical data)")
    print("  2. Restart the backend server")
    print("  3. Phase 3C APIs are available at /api/v1/admin/reports/*")


def downgrade():
    """Rollback Phase 3C schema changes (DANGER: data loss)."""
    print("[Phase3C Migration] Rolling back changes...")

    with engine.connect() as conn:
        tables = ["report_corrections", "monthly_revenue", "daily_revenue"]
        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                conn.commit()
                print(f"[Phase3C]   - Dropped table: {table}")
            except Exception as e:
                print(f"[Phase3C]   - WARNING dropping {table}: {e}")

    print("[Phase3C Migration] Rollback completed!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--downgrade":
            confirm = input("Are you sure you want to drop all Phase 3C tables? This will cause data loss! Type 'yes' to confirm: ")
            if confirm == "yes":
                downgrade()
            else:
                print("Aborted.")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python migrate_phase3c.py [--downgrade]")
    else:
        upgrade()
