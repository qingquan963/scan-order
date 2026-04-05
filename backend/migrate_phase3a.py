"""
Phase 3A Database Migration Script
Multi-tenant support + WeChat OAuth + Audit Logs

Usage:
    python migrate_phase3a.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine, Base
from app.models import Merchant  # noqa: F401 - needed to register models first


def upgrade():
    """Apply Phase 3A schema changes."""
    print("[Phase3A Migration] Starting database migration...")

    with engine.connect() as conn:
        # 1. Add status column to merchants table (if not exists)
        print("[Phase3A] Adding 'status' column to merchants table...")
        try:
            conn.execute(text("ALTER TABLE merchants ADD COLUMN status VARCHAR(20) DEFAULT 'active'"))
            conn.commit()
            print("[Phase3A]   - merchants.status column added (default: 'active')")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[Phase3A]   - merchants.status column already exists, skipping")
            else:
                print(f"[Phase3A]   - WARNING: {e}")

        # 2. Create platform_admins table
        print("[Phase3A] Creating platform_admins table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS platform_admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'admin',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("[Phase3A]   - platform_admins table created")

        # 3. Create merchant_users table
        print("[Phase3A] Creating merchant_users table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS merchant_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(255),
                wx_openid VARCHAR(100) UNIQUE,
                wx_unionid VARCHAR(100),
                role VARCHAR(20) NOT NULL DEFAULT 'owner',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """))
        conn.commit()
        print("[Phase3A]   - merchant_users table created")

        # Create index on merchant_users
        print("[Phase3A] Creating indexes on merchant_users...")
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_merchant_users_merchant_id ON merchant_users(merchant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_merchant_users_username ON merchant_users(username)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3A]   - Index creation warning: {e}")

        # 4. Create wx_auth_states table
        print("[Phase3A] Creating wx_auth_states table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wx_auth_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state VARCHAR(64) NOT NULL UNIQUE,
                redirect_uri VARCHAR(500),
                merchant_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP
            )
        """))
        conn.commit()
        print("[Phase3A]   - wx_auth_states table created")

        # Create index on wx_auth_states
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wx_auth_states_state ON wx_auth_states(state)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3A]   - Index creation warning: {e}")

        # 5. Create wx_refresh_tokens table
        print("[Phase3A] Creating wx_refresh_tokens table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wx_refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_user_id INTEGER NOT NULL,
                refresh_token VARCHAR(64) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                FOREIGN KEY (merchant_user_id) REFERENCES merchant_users(id)
            )
        """))
        conn.commit()
        print("[Phase3A]   - wx_refresh_tokens table created")

        # Create index on wx_refresh_tokens
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wx_refresh_tokens_user ON wx_refresh_tokens(merchant_user_id)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3A]   - Index creation warning: {e}")

        # 6. Create audit_logs table
        print("[Phase3A] Creating audit_logs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_type VARCHAR(20),
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id INTEGER,
                merchant_id INTEGER,
                details TEXT,
                ip_address VARCHAR(50),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("[Phase3A]   - audit_logs table created")

        # Create indexes on audit_logs
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_merchant_id ON audit_logs(merchant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3A]   - Index creation warning: {e}")

        # 7. Create merchant_users_auth table for JWT tokens
        print("[Phase3A] Creating merchant_tokens table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS merchant_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_user_id INTEGER NOT NULL,
                token_hash VARCHAR(255) NOT NULL UNIQUE,
                token_type VARCHAR(20) NOT NULL DEFAULT 'access',
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                FOREIGN KEY (merchant_user_id) REFERENCES merchant_users(id)
            )
        """))
        conn.commit()
        print("[Phase3A]   - merchant_tokens table created")

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_merchant_tokens_user ON merchant_tokens(merchant_user_id)"))
            conn.commit()
        except Exception as e:
            print(f"[Phase3A]   - Index creation warning: {e}")

    print("[Phase3A Migration] Completed successfully!")
    print("")
    print("Summary of changes:")
    print("  - merchants: added 'status' column (default: 'active')")
    print("  - platform_admins: NEW table for platform admin accounts")
    print("  - merchant_users: NEW table for merchant user accounts (owner/staff)")
    print("  - wx_auth_states: NEW table for WeChat OAuth state management")
    print("  - wx_refresh_tokens: NEW table for 30-day WeChat refresh tokens")
    print("  - merchant_tokens: NEW table for merchant JWT token management")
    print("  - audit_logs: NEW table for data access audit trail")
    print("")
    print("Next steps:")
    print("  1. Update core/config.py with WeChat OAuth credentials")
    print("  2. Restart the backend server")
    print("  3. Use migrate_phase3a.py --seed to create default platform admin")


def seed():
    """Seed default data for Phase 3A."""
    import secrets
    from passlib.context import CryptContext
    from app.database import SessionLocal

    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

    db = SessionLocal()
    try:
        # Check if platform admin exists
        result = db.execute(text("SELECT id FROM platform_admins WHERE username = 'admin'")).first()
        if result:
            print("[Phase3A Seed] Platform admin 'admin' already exists, skipping seed.")
        else:
            # Create default platform admin: admin / admin123
            password_hash = pwd_context.hash("admin123")
            db.execute(
                text("""
                    INSERT INTO platform_admins (username, password_hash, role, is_active)
                    VALUES ('admin', :password_hash, 'super_admin', 1)
                """),
                {"password_hash": password_hash}
            )
            db.commit()
            print("[Phase3A Seed] Created default platform admin: admin / admin123")
    finally:
        db.close()


def downgrade():
    """Rollback Phase 3A schema changes (DANGER: data loss)."""
    print("[Phase3A Migration] Rolling back changes...")

    with engine.connect() as conn:
        tables = [
            "audit_logs",
            "wx_refresh_tokens",
            "wx_auth_states",
            "merchant_tokens",
            "merchant_users",
            "platform_admins",
        ]
        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                conn.commit()
                print(f"[Phase3A]   - Dropped table: {table}")
            except Exception as e:
                print(f"[Phase3A]   - WARNING dropping {table}: {e}")

        # Remove status column from merchants
        try:
            # SQLite doesn't support DROP COLUMN easily, so we skip it in rollback
            print("[Phase3A]   - Note: merchants.status column retained (SQLite limitation)")
        except Exception as e:
            print(f"[Phase3A]   - WARNING: {e}")

    print("[Phase3A Migration] Rollback completed!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--seed":
            seed()
        elif sys.argv[1] == "--downgrade":
            confirm = input("Are you sure you want to drop all Phase 3A tables? This will cause data loss! Type 'yes' to confirm: ")
            if confirm == "yes":
                downgrade()
            else:
                print("Aborted.")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python migrate_phase3a.py [--seed|--downgrade]")
    else:
        upgrade()
