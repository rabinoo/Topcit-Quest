from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlsplit

from api._utils import db_connect, json_response, cors_preflight


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Token is expected in query string: /api/users/verify?token=...
        try:
            qs = urlsplit(self.path).query
            params = parse_qs(qs)
            token = (params.get('token') or [''])[0].strip()
            if not token:
                return json_response(self, 400, { 'ok': False, 'error': 'Missing token' })
        except Exception as e:
            return json_response(self, 400, { 'ok': False, 'error': f'Invalid request: {e}' })

        conn = db_connect()
        if not conn:
            return json_response(self, 503, { 'ok': False, 'error': 'Database connection failed' })

        ok = False
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET email_verified = TRUE, email_verification_token = NULL WHERE email_verification_token = %s",
                        (token,)
                    )
                    ok = cur.rowcount > 0
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return json_response(self, 200 if ok else 404, { 'ok': ok })

    def do_GET(self):
        # Method not allowed
        return json_response(self, 405, { 'ok': False, 'error': 'Use POST' })

    def do_OPTIONS(self):
        return cors_preflight(self)