import os
import json
import ssl
import smtplib
import psycopg2
import hashlib
import datetime
try:
    import bcrypt  # optional; fallback to sha256
except Exception:
    bcrypt = None
from typing import Optional

try:
    # Load local .env for dev; Vercel uses dashboard envs.
    from dotenv import load_dotenv
    load_dotenv()
    secret_env_path = os.environ.get('DOTENV_PATH', '/etc/secrets/.env')
    if os.path.exists(secret_env_path):
        load_dotenv(secret_env_path, override=True)
except Exception:
    pass


def _with_sslmode(url: str) -> str:
    if not url:
        return url
    if 'sslmode=' in url:
        return url
    # Append sslmode=require for Neon
    if '?' in url:
        return url + '&sslmode=require'
    return url + '?sslmode=require'


def db_connect():
    url = _with_sslmode(os.environ.get('DATABASE_URL'))
    if not url:
        return None
    try:
        return psycopg2.connect(url)
    except Exception:
        return None


def send_email(to_addr: str, subject: str, text: str, html: Optional[str] = None) -> bool:
    host = os.environ.get('SMTP_HOST')
    port = int(os.environ.get('SMTP_PORT') or '587')
    user = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASS')
    from_addr = os.environ.get('SMTP_FROM') or user
    use_ssl = str(os.environ.get('SMTP_USE_SSL') or 'false').lower() in ('1','true','yes')

    if not host or not port or not user or not password or not from_addr:
        return False

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port)
            server.ehlo()
            try:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            except Exception:
                pass
        server.login(user, password)
        # Build message
        boundary = "plain-html"
        msg = [
            f"From: {from_addr}",
            f"To: {to_addr}",
            f"Subject: {subject}",
            "MIME-Version: 1.0",
            f"Content-Type: multipart/alternative; boundary=\"{boundary}\"",
            "",
            f"--{boundary}",
            "Content-Type: text/plain; charset=utf-8",
            "",
            text,
        ]
        if html:
            msg += [
                f"--{boundary}",
                "Content-Type: text/html; charset=utf-8",
                "",
                html,
            ]
        msg += [f"--{boundary}--", ""]
        server.sendmail(from_addr, [to_addr], "\r\n".join(msg).encode('utf-8'))
        server.quit()
        return True
    except Exception:
        return False


def _set_cors(handler):
    origin = handler.headers.get('Origin') or ''
    allow = os.environ.get('CORS_ALLOW_ORIGINS')
    if allow:
        allowed = [o.strip() for o in allow.split(',') if o.strip()]
        ao = origin if origin and origin in allowed else (allowed[0] if allowed else '*')
    else:
        ao = origin or '*'
    handler.send_header('Access-Control-Allow-Origin', ao)
    handler.send_header('Vary', 'Origin')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
    handler.send_header('Access-Control-Max-Age', '86400')


def cors_preflight(handler):
    handler.send_response(204)
    _set_cors(handler)
    handler.end_headers()


def json_response(handler, status_code: int, payload: dict):
    data = json.dumps(payload).encode('utf-8')
    handler.send_response(status_code)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(data)))
    _set_cors(handler)
    handler.end_headers()
    handler.wfile.write(data)


def get_bearer_token(handler) -> Optional[str]:
    auth = handler.headers.get('Authorization') or ''
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return None


def get_user_by_token(token: str) -> Optional[dict]:
    if not token:
        return None
    conn = db_connect()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.username, u.email, u.name, u.xp_total, u.level_idx, u.xp_in_level, u.wallet, u.email_verified, u.is_admin
                    FROM sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.token = %s AND s.revoked = FALSE AND s.expires_at > NOW()
                    """,
                    (token,)
                )
                row = cur.fetchone()
                if row:
                    return {
                        'id': row[0], 'username': row[1], 'email': row[2], 'name': row[3],
                        'xp_total': row[4], 'level_idx': row[5], 'xp_in_level': row[6], 'wallet': row[7],
                        'email_verified': bool(row[8]), 'is_admin': bool(row[9])
                    }
                return None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def verify_password(plain: str, stored_hash: str) -> bool:
    try:
        if bcrypt and stored_hash:
            return bcrypt.checkpw(plain.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        pass
    try:
        return stored_hash == hashlib.sha256(plain.encode('utf-8')).hexdigest()
    except Exception:
        return False


def issue_session_token(user_id: str) -> Optional[str]:
    import secrets
    token = secrets.token_hex(32)
    expires = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    conn = db_connect()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES (%s, %s, %s)", (token, user_id, expires))
                return token
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass