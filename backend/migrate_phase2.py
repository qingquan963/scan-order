"""
Database migration script: Phase 2
- Add payment_token, payment_token_used, paid_at columns to orders table
- Fix invalid mode values in merchant_settings
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "scan_order.db")


def migrate():
    if not os.path.exists(DB_PATH):
        print("[SKIP] Database file does not exist, skipping migration")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Check existing columns in orders table
    cursor.execute("PRAGMA table_info(orders)")
    columns = {row[1] for row in cursor.fetchall()}

    if "payment_token" not in columns:
        print("[1] Adding payment_token column...")
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_token VARCHAR(36)")
        print("  [OK] payment_token column added")

    if "payment_token_used" not in columns:
        print("[2] Adding payment_token_used column...")
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_token_used INTEGER DEFAULT 0")
        print("  [OK] payment_token_used column added")

    if "paid_at" not in columns:
        print("[3] Adding paid_at column...")
        cursor.execute("ALTER TABLE orders ADD COLUMN paid_at TIMESTAMP")
        print("  [OK] paid_at column added")

    # 2. Fix invalid merchant_settings.mode values
    print("[4] Checking merchant_settings.mode...")
    cursor.execute("SELECT merchant_id, mode FROM merchant_settings")
    rows = cursor.fetchall()
    for merchant_id, mode in rows:
        if mode not in ("counter_pay", "credit_pay"):
            print(f"  Fixing merchant_id={merchant_id}, mode='{mode}' -> 'counter_pay'")
            cursor.execute(
                "UPDATE merchant_settings SET mode = ? WHERE merchant_id = ?",
                ("counter_pay", merchant_id)
            )
    print("  [OK] merchant_settings.mode invalid values fixed")

    conn.commit()
    conn.close()
    print("\n[MIGRATION COMPLETE]")


if __name__ == "__main__":
    migrate()
