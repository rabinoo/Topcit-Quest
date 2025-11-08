from typing import Optional

from lib._utils import db_connect


DDL_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    name TEXT,
    password_hash TEXT NOT NULL,
    xp_total INTEGER NOT NULL DEFAULT 0,
    level_idx INTEGER NOT NULL DEFAULT 0,
    xp_in_level INTEGER NOT NULL DEFAULT 0,
    wallet INTEGER NOT NULL DEFAULT 0,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    email_verification_token TEXT,
    reset_token TEXT,
    reset_token_expires TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

DDL_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE
)
"""

DDL_MODULE_STORE = """
CREATE TABLE IF NOT EXISTS module_store (
    id TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def ensure_schema() -> bool:
    """Ensure required tables exist; safe to call per-request."""
    conn = db_connect()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL_USERS)
                # Add missing columns if table existed earlier
                try: cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE")
                except Exception: pass
                try: cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE")
                except Exception: pass
                try: cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token TEXT")
                except Exception: pass
                try: cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token TEXT")
                except Exception: pass
                try: cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMPTZ")
                except Exception: pass

                cur.execute(DDL_SESSIONS)
                cur.execute(DDL_MODULE_STORE)
        return True
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass