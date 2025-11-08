from http.server import BaseHTTPRequestHandler
import json
import hashlib
import uuid

from lib._utils import db_connect, json_response, cors_preflight
from lib._schema import ensure_schema

try:
    import bcrypt  # optional; fallback to sha256
except Exception:
    bcrypt = None


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Parse JSON body
        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode('utf-8'))
        except Exception as e:
            return json_response(self, 400, { 'ok': False, 'error': f'Invalid JSON: {e}' })

        name = str(payload.get('name') or '').strip()
        username = str(payload.get('username') or '').strip()
        email = str(payload.get('email') or '').strip()
        password = str(payload.get('password') or '')

        if not name or not username or not email or not password:
            return json_response(self, 400, { 'ok': False, 'error': 'Missing required fields' })
        if '@' not in email:
            return json_response(self, 400, { 'ok': False, 'error': 'Enter a valid email address' })
        if len(password) < 6:
            return json_response(self, 400, { 'ok': False, 'error': 'Password must be at least 6 characters' })

        # Hash password (prefer bcrypt when available)
        try:
            if bcrypt:
                pwd_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            else:
                pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        except Exception:
            return json_response(self, 500, { 'ok': False, 'error': 'Failed to hash password' })

        # Ensure DB schema exists (safe to call per-request)
        ensure_schema()

        conn = db_connect()
        if not conn:
            return json_response(self, 503, { 'ok': False, 'error': 'Database connection failed' })

        user_id = str(uuid.uuid4())
        ok = False
        err_msg = None

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
            msg = str(e)
            if 'users_email_key' in msg or ('duplicate key value' in msg and '(email)=' in msg):
                err_msg = 'Email Already Exists'
            elif 'users_username_key' in msg or ('duplicate key value' in msg and '(username)=' in msg):
                err_msg = 'Username Already Exists'
            else:
                err_msg = 'Registration failed'
            ok = False
        finally:
            try:
                conn.close()
            except Exception:
                pass

        user_payload = None
        if ok:
            # Load minimal profile for client
            conn2 = db_connect()
            if conn2:
                try:
                    with conn2:
                        with conn2.cursor() as cur2:
                            cur2.execute(
                                "SELECT id, username, email, name, xp_total, level_idx, xp_in_level, wallet, email_verified, is_admin FROM users WHERE id = %s",
                                (user_id,)
                            )
                            r = cur2.fetchone()
                            if r:
                                user_payload = {
                                    'id': r[0], 'username': r[1], 'email': r[2], 'name': r[3],
                                    'xp_total': r[4], 'level_idx': r[5], 'xp_in_level': r[6], 'wallet': r[7],
                                    'email_verified': bool(r[8]), 'is_admin': bool(r[9])
                                }
                finally:
                    try:
                        conn2.close()
                    except Exception:
                        pass

        status = 200 if ok else 409
        return json_response(self, status, { 'ok': ok, 'error': err_msg, 'user': user_payload })

    def do_GET(self):
        # Method not allowed
        return json_response(self, 405, { 'ok': False, 'error': 'Use POST' })

    def do_OPTIONS(self):
        return cors_preflight(self)