import os
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import re
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets
try:
    import bcrypt
except Exception:
    bcrypt = None

# Optional Postgres driver (Neon)
DB_ENABLED = False

# SMTP email configuration
SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
SMTP_FROM = os.environ.get('SMTP_FROM') or SMTP_USER
SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1', 'true', 'yes')

def send_email(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_FROM):
        return False
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_FROM, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            try:
                s.starttls()
                s.ehlo()
            except Exception:
                pass
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_FROM, [to_email], msg.as_string())
    return True
DB_URL = os.environ.get('DATABASE_URL', '').strip()
conn_params = None
try:
    import psycopg2  # psycopg2-binary
    if DB_URL:
        # Neon requires SSL; append sslmode=require if not present
        if 'sslmode=' not in DB_URL:
            if '?' in DB_URL:
                DB_URL = DB_URL + '&sslmode=require'
            else:
                DB_URL = DB_URL + '?sslmode=require'
        conn_params = DB_URL
        DB_ENABLED = True
except Exception as _:
    DB_ENABLED = False

DOCS_DIR = os.path.join(os.getcwd(), 'docs')
UPLOAD_DIR = os.path.join(DOCS_DIR, 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)

def db_connect():
    if not DB_ENABLED:
        return None
    try:
        return psycopg2.connect(conn_params)
    except Exception as e:
        print(f"[DB] Connection failed: {e}")
        return None

def db_init():
    if not DB_ENABLED:
        print("[DB] DATABASE_URL not set; API will use localStorage fallback.")
        return False
    conn = db_connect()
    if not conn:
        print("[DB] Could not connect; API will use localStorage fallback.")
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS module_store (
                        id TEXT PRIMARY KEY,
                        data JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                # Basic users table for credential auth and progress
                cur.execute(
                    """
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
                )
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

                # Sessions for token-based auth
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        token TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        expires_at TIMESTAMPTZ NOT NULL,
                        revoked BOOLEAN NOT NULL DEFAULT FALSE
                    )
                    """
                )

                # Activity logs per quest/action
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        course_id TEXT,
                        event_type TEXT NOT NULL,
                        xp_awarded INTEGER DEFAULT 0,
                        coins_awarded INTEGER DEFAULT 0,
                        metadata JSONB,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
        print("[DB] Initialized module_store table.")
        print("[DB] Initialized users, sessions, and activity_logs tables.")
        return True
    finally:
        conn.close()

def db_upsert_modules(mods):
    """Store entire modules array under a single key for simplicity."""
    if not DB_ENABLED:
        return False
    conn = db_connect()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO module_store(id, data, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (id)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                    """,
                    ('custom_modules', json.dumps(mods))
                )
        return True
    except Exception as e:
        print(f"[DB] Upsert failed: {e}")
        return False
    finally:
        conn.close()

def db_fetch_modules():
    if not DB_ENABLED:
        return None
    conn = db_connect()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM module_store WHERE id = %s", ('custom_modules',))
                row = cur.fetchone()
                if row and row[0] is not None:
                    # row[0] may be a dict already depending on driver setup
                    return row[0] if isinstance(row[0], (list, dict)) else json.loads(row[0])
        return None
    except Exception as e:
        print(f"[DB] Fetch failed: {e}")
        return None
    finally:
        conn.close()

class UploadHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve files out of the docs directory
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    # ---- Auth helpers ----
    def _get_bearer_token(self):
        auth = self.headers.get('Authorization', '')
        try:
            low = auth.lower()
            if low.startswith('bearer '):
                return auth[7:].strip()
        except Exception:
            pass
        return ''

    def _get_user_by_token(self):
        if not DB_ENABLED:
            return None
        token = self._get_bearer_token()
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
        except Exception:
            return None
        finally:
            conn.close()
        return None

    def do_POST(self):
        # --- Users: Register ---
        if self.path == '/api/users/register':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                username = (payload.get('username') or '').strip()
                email = (payload.get('email') or '').strip()
                name = (payload.get('name') or '').strip()
                password = str(payload.get('password') or '')
                if not username or not email or not password:
                    raise ValueError('Missing required fields')
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return

            # Hash password (prefer bcrypt when available)
            if bcrypt:
                pwd_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            else:
                pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            user_id = str(uuid.uuid4())
            ok = False
            err_msg = None
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO users(id, username, email, name, password_hash)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (user_id, username, email, name, pwd_hash)
                        )
                        ok = True
            except Exception as e:
                # Simplify error messaging for duplicate keys
                msg = str(e)
                # Prefer concise, user-friendly messages
                if 'users_email_key' in msg or ('duplicate key value' in msg and '(email)=' in msg):
                    err_msg = 'Email Already Exists'
                elif 'users_username_key' in msg or ('duplicate key value' in msg and '(username)=' in msg):
                    err_msg = 'Username Already Exists'
                else:
                    err_msg = 'Registration failed'
                ok = False
            finally:
                conn.close()

            user_payload = None
            if ok:
                # Load minimal profile for client
                conn3 = db_connect()
                if conn3:
                    try:
                        with conn3:
                            with conn3.cursor() as cur3:
                                cur3.execute("SELECT id, username, email, name, xp_total, level_idx, xp_in_level, wallet, email_verified, is_admin FROM users WHERE id = %s", (user_id,))
                                r = cur3.fetchone()
                                if r:
                                    user_payload = {
                                        'id': r[0], 'username': r[1], 'email': r[2], 'name': r[3],
                                        'xp_total': r[4], 'level_idx': r[5], 'xp_in_level': r[6], 'wallet': r[7],
                                        'email_verified': bool(r[8]), 'is_admin': bool(r[9])
                                    }
                    finally:
                        conn3.close()
            resp = { 'ok': ok, 'error': err_msg, 'user': user_payload }
            data = json.dumps(resp).encode('utf-8')
            self.send_response(200 if ok else 409)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Email verification start (POST) ---
        if self.path == '/api/users/verify/start':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                identity = (payload.get('identity') or '').strip()  # email
                if not identity or '@' not in identity:
                    raise ValueError('Provide an email')
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return
            token = secrets.token_urlsafe(32)
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE users SET email_verification_token = %s WHERE email = %s", (token, identity))
                        ok = cur.rowcount > 0
            finally:
                conn.close()

            email_sent = False
            send_error = None
            if ok:
                try:
                    host = self.headers.get('Host') or 'localhost:8000'
                    verify_page_url = f"http://{host}/verify.html?token={token}"
                    api_url = f"http://{host}/api/users/verify?token={token}"
                    subject = "Verify your Topcit Quest account"
                    text = (
                        "Thanks for signing up!\n\n"
                        f"Click the link to verify your email: {verify_page_url}\n\n"
                        "If the above link doesn't work, you can use this direct link: "
                        f"{api_url}\n"
                    )
                    html = (
                        f"<p>Thanks for signing up!</p>"
                        f"<p><a href='{verify_page_url}'>Click here to verify your email</a></p>"
                        f"<p>If the above link doesn't work, use this direct link:<br/><code>{api_url}</code></p>"
                    )
                    email_sent = send_email(identity, subject, text, html)
                except Exception as e:
                    send_error = str(e)

            body = { 'ok': ok, 'token': token if ok else None, 'email_sent': email_sent }
            if send_error:
                body['email_error'] = send_error
            data = json.dumps(body).encode('utf-8')
            self.send_response(200 if ok else 404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Login ---
        if self.path == '/api/users/login':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                identity = (payload.get('identity') or '').strip()  # username or email
                password = str(payload.get('password') or '')
                if not identity or not password:
                    raise ValueError('Missing credentials')
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return

            pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            user = None
            try:
                with conn:
                    with conn.cursor() as cur:
                        # Decide whether identity is email or username
                        is_email = '@' in identity
                        if is_email:
                            cur.execute("SELECT id, username, email, name, xp_total, level_idx, xp_in_level, wallet, email_verified, is_admin, password_hash FROM users WHERE email = %s", (identity,))
                        else:
                            cur.execute("SELECT id, username, email, name, xp_total, level_idx, xp_in_level, wallet, email_verified, is_admin, password_hash FROM users WHERE username = %s", (identity,))
                        row = cur.fetchone()
                        if row:
                            # Verify password
                            stored = row[10] or ''
                            ok = False
                            try:
                                if bcrypt and stored:
                                    ok = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
                                else:
                                    ok = (stored == hashlib.sha256(password.encode('utf-8')).hexdigest())
                            except Exception:
                                ok = False
                            if ok:
                                user = {
                                    'id': row[0], 'username': row[1], 'email': row[2], 'name': row[3],
                                    'xp_total': row[4], 'level_idx': row[5], 'xp_in_level': row[6], 'wallet': row[7],
                                    'email_verified': bool(row[8]), 'is_admin': bool(row[9])
                                }
            finally:
                conn.close()

            if not user:
                payload = { 'ok': False, 'error': 'Invalid credentials' }
                data = json.dumps(payload).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            # Enforce verified email before issuing session
            if not user.get('email_verified'):
                payload = { 'ok': False, 'error': 'Email not verified. Please check your inbox.', 'needs_verification': True }
                data = json.dumps(payload).encode('utf-8')
                self.send_response(403)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            # Issue session token
            token = secrets.token_hex(32)
            expires = datetime.utcnow() + timedelta(days=7)
            conn2 = db_connect()
            if conn2:
                try:
                    with conn2:
                        with conn2.cursor() as cur2:
                            cur2.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES (%s, %s, %s)", (token, user['id'], expires))
                finally:
                    conn2.close()
            payload = { 'ok': True, 'user': user, 'token': token }
            data = json.dumps(payload).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Email verification complete (by token, POST) ---
        if self.path.startswith('/api/users/verify'):
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                qs = self.path.split('?', 1)[1] if '?' in self.path else ''
                params = dict([kv.split('=', 1) for kv in qs.split('&') if '=' in kv])
                token = params.get('token', '').strip()
                if not token:
                    raise ValueError('Missing token')
            except Exception as e:
                self.send_error(400, f'Invalid request: {e}')
                return
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE users SET email_verified = TRUE, email_verification_token = NULL WHERE email_verification_token = %s", (token,))
                        ok = cur.rowcount > 0
            finally:
                conn.close()
            data = json.dumps({ 'ok': ok }).encode('utf-8')
            self.send_response(200 if ok else 404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == '/api/modules':
            # Expect a JSON array of modules
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                mods = json.loads(raw.decode('utf-8'))
                if not isinstance(mods, list):
                    raise ValueError('Expected an array of modules')
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return
            # Admin-only: require valid token with is_admin
            user = self._get_user_by_token()
            if not user or not user.get('is_admin'):
                self.send_error(403, 'Admin authorization required')
                return
            ok = db_upsert_modules(mods)
            payload = { 'ok': bool(ok), 'source': 'neon' if ok else 'fallback' }
            data = json.dumps(payload).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path != '/upload':
            self.send_error(404, 'Not Found')
            return

        ctype = self.headers.get('Content-Type', '')
        if not ctype.startswith('multipart/form-data'):
            self.send_error(400, 'Expected multipart/form-data')
            return

        content_length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(content_length)

        # Extract boundary
        m = re.search(r"boundary=([\-A-Za-z0-9'()+_.,/:=?]+)", ctype)
        if not m:
            self.send_error(400, 'Missing boundary')
            return
        boundary = m.group(1)
        b = ('--' + boundary).encode('utf-8')

        parts = raw.split(b)
        file_bytes = None
        orig_name = ''
        for part in parts:
            if not part or part in (b'--\r\n', b'--'):
                continue
            # Separate headers and content
            if b"\r\n\r\n" not in part:
                continue
            head, body = part.split(b"\r\n\r\n", 1)
            # Trim ending CRLF and boundary close
            body = body.rstrip(b"\r\n")
            headers_text = head.decode('utf-8', errors='ignore')
            if 'name="file"' in headers_text:
                fnm = re.search(r'filename="(.*?)"', headers_text)
                orig_name = fnm.group(1) if fnm else ''
                file_bytes = body
                break

        if not file_bytes:
            self.send_error(400, 'No file uploaded')
            return

        orig_name = os.path.basename(orig_name or '')
        base, ext = os.path.splitext(orig_name)
        ts = int(time.time() * 1000)
        safe_base = base[:50].replace(' ', '_') or 'image'
        fname = f"{safe_base}-{ts}{ext or '.png'}"
        fpath = os.path.join(UPLOAD_DIR, fname)

        with open(fpath, 'wb') as out:
            out.write(file_bytes)

        rel_url = f"/uploads/{fname}"
        rel_path = f"uploads/{fname}"

        payload = { 'url': rel_url, 'path': rel_path, 'filename': fname }
        data = json.dumps(payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        # --- Users: Get profile (by Authorization token) ---
        if self.path.startswith('/api/users/me'):
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            user = self._get_user_by_token()
            if not user:
                self.send_error(401, 'Unauthorized')
                return
            data = json.dumps(user).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == '/api/modules':
            mods = db_fetch_modules()
            # If no data in DB, return 200 with empty list (frontend will fallback to localStorage)
            payload = mods if isinstance(mods, list) else []
            data = json.dumps(payload).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        # Fallback to static file serving
        return super().do_GET()

    def do_PUT(self):
        # --- Users: Update progress (Authorization required) ---
        if self.path == '/api/users/progress':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                xp_total = int(payload.get('xp_total') or 0)
                level_idx = int(payload.get('level_idx') or 0)
                xp_in_level = int(payload.get('xp_in_level') or 0)
                wallet = int(payload.get('wallet') or 0)
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return
            user = self._get_user_by_token()
            if not user:
                self.send_error(401, 'Unauthorized')
                return
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE users
                            SET xp_total = %s, level_idx = %s, xp_in_level = %s, wallet = %s
                            WHERE id = %s
                            """,
                            (xp_total, level_idx, xp_in_level, wallet, user['id'])
                        )
                        ok = cur.rowcount > 0
            finally:
                conn.close()

            resp = { 'ok': ok }
            data = json.dumps(resp).encode('utf-8')
            self.send_response(200 if ok else 404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Email verification start ---
        if self.path == '/api/users/verify/start':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                identity = (payload.get('identity') or '').strip()  # email
                if not identity or '@' not in identity:
                    raise ValueError('Provide an email')
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return
            token = secrets.token_urlsafe(32)
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE users SET email_verification_token = %s WHERE email = %s", (token, identity))
                        ok = cur.rowcount > 0
            finally:
                conn.close()
            data = json.dumps({ 'ok': ok, 'token': token if ok else None }).encode('utf-8')
            self.send_response(200 if ok else 404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Email verification complete (by token) ---
        if self.path.startswith('/api/users/verify'):
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                qs = self.path.split('?', 1)[1] if '?' in self.path else ''
                params = dict([kv.split('=', 1) for kv in qs.split('&') if '=' in kv])
                token = params.get('token', '').strip()
                if not token:
                    raise ValueError('Missing token')
            except Exception as e:
                self.send_error(400, f'Invalid request: {e}')
                return
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE users SET email_verified = TRUE, email_verification_token = NULL WHERE email_verification_token = %s", (token,))
                        ok = cur.rowcount > 0
            finally:
                conn.close()
            data = json.dumps({ 'ok': ok }).encode('utf-8')
            self.send_response(200 if ok else 404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Password reset start ---
        if self.path == '/api/users/reset/start':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                identity = (payload.get('identity') or '').strip()  # email
                if not identity or '@' not in identity:
                    raise ValueError('Provide an email')
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return
            token = secrets.token_urlsafe(32)
            expires = datetime.utcnow() + timedelta(hours=1)
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE email = %s", (token, expires, identity))
                        ok = cur.rowcount > 0
            finally:
                conn.close()
            data = json.dumps({ 'ok': ok, 'token': token if ok else None }).encode('utf-8')
            self.send_response(200 if ok else 404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Password reset complete ---
        if self.path == '/api/users/reset/complete':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                token = (payload.get('token') or '').strip()
                new_password = str(payload.get('password') or '')
                if not token or not new_password:
                    raise ValueError('Missing token or password')
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return
            # Hash new password
            if bcrypt:
                pwd_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            else:
                pwd_hash = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE users
                            SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL
                            WHERE reset_token = %s AND reset_token_expires > NOW()
                            """,
                            (pwd_hash, token)
                        )
                        ok = cur.rowcount > 0
            finally:
                conn.close()
            data = json.dumps({ 'ok': ok }).encode('utf-8')
            self.send_response(200 if ok else 400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # --- Users: Activity log create ---
        if self.path == '/api/users/activity':
            if not DB_ENABLED:
                self.send_error(503, 'Database not available')
                return
            user = self._get_user_by_token()
            if not user:
                self.send_error(401, 'Unauthorized')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode('utf-8'))
                course_id = (payload.get('course_id') or '').strip()
                event_type = (payload.get('event_type') or '').strip() or 'course_completed'
                xp_awarded = int(payload.get('xp_awarded') or 0)
                coins_awarded = int(payload.get('coins_awarded') or 0)
                metadata = payload.get('metadata') if isinstance(payload.get('metadata'), (dict, list)) else None
            except Exception as e:
                self.send_error(400, f'Invalid JSON: {e}')
                return
            log_id = str(uuid.uuid4())
            conn = db_connect()
            if not conn:
                self.send_error(503, 'Database connection failed')
                return
            ok = False
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO activity_logs(id, user_id, course_id, event_type, xp_awarded, coins_awarded, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                            """,
                            (log_id, user['id'], course_id or None, event_type, xp_awarded, coins_awarded, json.dumps(metadata) if metadata is not None else None)
                        )
                        ok = True
            finally:
                conn.close()
            data = json.dumps({ 'ok': ok, 'id': log_id }).encode('utf-8')
            self.send_response(200 if ok else 500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    db_init()
    httpd = ThreadingHTTPServer(('', port), UploadHandler)
    print(f"Serving docs on port {port} with upload endpoint at /upload and API /api/modules")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()