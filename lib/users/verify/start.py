from http.server import BaseHTTPRequestHandler
import json
import secrets
from urllib.parse import urlsplit

from lib._utils import db_connect, send_email, json_response, cors_preflight


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode('utf-8'))
        except Exception as e:
            return json_response(self, 400, { 'ok': False, 'error': f'Invalid JSON: {e}' })

        identity = str(payload.get('identity') or '').strip()
        if not identity or '@' not in identity:
            return json_response(self, 400, { 'ok': False, 'error': 'Provide an email' })

        token = secrets.token_urlsafe(32)
        conn = db_connect()
        if not conn:
            return json_response(self, 503, { 'ok': False, 'error': 'Database connection failed' })

        ok = False
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET email_verification_token = %s WHERE email = %s", (token, identity))
                    ok = cur.rowcount > 0
        finally:
            try:
                conn.close()
            except Exception:
                pass

        email_sent = False
        send_error = None
        if ok:
            try:
                # Prefer forwarded proto; default to https on Vercel
                proto = self.headers.get('x-forwarded-proto', 'https')
                host = self.headers.get('host') or 'localhost:3000'
                verify_page_url = f"{proto}://{host}/verify.html?token={token}"
                api_url = f"{proto}://{host}/api/users/verify?token={token}"
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
        return json_response(self, 200 if ok else 404, body)

    def do_GET(self):
        # Method not allowed
        return json_response(self, 405, { 'ok': False, 'error': 'Use POST' })

    def do_OPTIONS(self):
        return cors_preflight(self)