from http.server import BaseHTTPRequestHandler

from .._utils import json_response, get_bearer_token, get_user_by_token, cors_preflight


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = get_bearer_token(self)
        if not token:
            return json_response(self, 401, { 'ok': False, 'error': 'Unauthorized' })
        user = get_user_by_token(token)
        if not user:
            return json_response(self, 401, { 'ok': False, 'error': 'Unauthorized' })
        return json_response(self, 200, user)

    def do_POST(self):
        return json_response(self, 405, { 'ok': False, 'error': 'Use GET' })

    def do_OPTIONS(self):
        return cors_preflight(self)