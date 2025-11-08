from http.server import BaseHTTPRequestHandler
import json

from .._utils import db_connect, json_response, verify_password, issue_session_token, cors_preflight
from .._schema import ensure_schema


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode('utf-8'))
        except Exception as e:
            return json_response(self, 400, { 'ok': False, 'error': f'Invalid JSON: {e}' })

        identity = str(payload.get('identity') or '').strip()
        password = str(payload.get('password') or '')
        if not identity or not password:
            return json_response(self, 400, { 'ok': False, 'error': 'Missing credentials' })

        # Ensure DB schema exists (safe to call per-request)
        ensure_schema()

        conn = db_connect()
        if not conn:
            return json_response(self, 503, { 'ok': False, 'error': 'Database connection failed' })

        user = None
        try:
            with conn:
                with conn.cursor() as cur:
                    is_email = '@' in identity
                    if is_email:
                        cur.execute("SELECT id, username, email, name, xp_total, level_idx, xp_in_level, wallet, email_verified, is_admin, password_hash FROM users WHERE email = %s", (identity,))
                    else:
                        cur.execute("SELECT id, username, email, name, xp_total, level_idx, xp_in_level, wallet, email_verified, is_admin, password_hash FROM users WHERE username = %s", (identity,))
                    row = cur.fetchone()
                    if row:
                        stored = row[10] or ''
                        if verify_password(password, stored):
                            user = {
                                'id': row[0], 'username': row[1], 'email': row[2], 'name': row[3],
                                'xp_total': row[4], 'level_idx': row[5], 'xp_in_level': row[6], 'wallet': row[7],
                                'email_verified': bool(row[8]), 'is_admin': bool(row[9])
                            }
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if not user:
            return json_response(self, 401, { 'ok': False, 'error': 'Invalid credentials' })

        if not user.get('email_verified'):
            return json_response(self, 403, { 'ok': False, 'error': 'Email not verified. Please check your inbox.', 'needs_verification': True })

        token = issue_session_token(user['id'])
        if not token:
            return json_response(self, 503, { 'ok': False, 'error': 'Could not issue session' })

        return json_response(self, 200, { 'ok': True, 'user': user, 'token': token })

    def do_GET(self):
        return json_response(self, 405, { 'ok': False, 'error': 'Use POST' })

    def do_OPTIONS(self):
        return cors_preflight(self)