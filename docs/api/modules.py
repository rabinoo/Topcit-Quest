from http.server import BaseHTTPRequestHandler
import json

from api._utils import db_connect, json_response, get_bearer_token, get_user_by_token, cors_preflight
from api._schema import ensure_schema


def _fetch_modules():
    conn = db_connect()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM module_store WHERE id = %s", ('custom_modules',))
                row = cur.fetchone()
                if row and row[0] is not None:
                    return row[0] if isinstance(row[0], (list, dict)) else json.loads(row[0])
        return None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _upsert_modules(mods):
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
                    ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                    """,
                    ('custom_modules', json.dumps(mods))
                )
                return True
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Ensure schema exists for module_store
        ensure_schema()
        # Return published modules from DB; 503 if DB unavailable
        data = _fetch_modules()
        if data is None:
            return json_response(self, 503, { 'ok': False, 'error': 'Database unavailable' })
        return json_response(self, 200, data if isinstance(data, list) else [])

    def do_POST(self):
        # Ensure schema exists for module_store
        ensure_schema()
        # Require admin via Bearer token, then upsert modules array
        token = get_bearer_token(self)
        user = get_user_by_token(token) if token else None
        if not user or not user.get('is_admin'):
            return json_response(self, 403, { 'ok': False, 'error': 'Admin required' })

        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode('utf-8'))
        except Exception as e:
            return json_response(self, 400, { 'ok': False, 'error': f'Invalid JSON: {e}' })

        if not isinstance(payload, list):
            return json_response(self, 400, { 'ok': False, 'error': 'Expected an array of modules' })

        ok = _upsert_modules(payload)
        return json_response(self, 200 if ok else 503, { 'ok': ok })

    def do_PUT(self):
        # Method not allowed
        return json_response(self, 405, { 'ok': False, 'error': 'Use GET or POST' })

    def do_DELETE(self):
        return json_response(self, 405, { 'ok': False, 'error': 'Use GET or POST' })

    def do_OPTIONS(self):
        return cors_preflight(self)