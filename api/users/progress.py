from http.server import BaseHTTPRequestHandler
import json

from api._utils import json_response, get_bearer_token, get_user_by_token, db_connect


class handler(BaseHTTPRequestHandler):
    def do_PUT(self):
        token = get_bearer_token(self)
        if not token:
            return json_response(self, 401, { 'ok': False, 'error': 'Unauthorized' })
        user = get_user_by_token(token)
        if not user:
            return json_response(self, 401, { 'ok': False, 'error': 'Unauthorized' })

        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode('utf-8'))
            xp_total = int(payload.get('xp_total') or 0)
            level_idx = int(payload.get('level_idx') or 0)
            xp_in_level = int(payload.get('xp_in_level') or 0)
            wallet = int(payload.get('wallet') or 0)
        except Exception as e:
            return json_response(self, 400, { 'ok': False, 'error': f'Invalid JSON: {e}' })

        conn = db_connect()
        if not conn:
            return json_response(self, 503, { 'ok': False, 'error': 'Database connection failed' })

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
            try:
                conn.close()
            except Exception:
                pass

        return json_response(self, 200 if ok else 404, { 'ok': ok })

    def do_GET(self):
        return json_response(self, 405, { 'ok': False, 'error': 'Use PUT' })