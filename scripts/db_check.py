import os
import psycopg2

DB_URL = os.environ.get("DATABASE_URL") or "postgresql://neondb_owner:npg_1kFHveWgZDy6@ep-frosty-dew-a1yy9upy-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def check_email(email: str):
    conn = psycopg2.connect(DB_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, email_verification_token, email_verified FROM users WHERE email = %s",
                    (email,)
                )
                rows = cur.fetchall()
                print("rows:", rows)
    finally:
        conn.close()

if __name__ == "__main__":
    check_email("krbucang@gmail.com")