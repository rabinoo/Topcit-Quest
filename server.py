import os
import json
import time
import shutil
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import re

DOCS_DIR = os.path.join(os.getcwd(), 'docs')
UPLOAD_DIR = os.path.join(DOCS_DIR, 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)

class UploadHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve files out of the docs directory
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    def do_POST(self):
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    httpd = ThreadingHTTPServer(('', port), UploadHandler)
    print(f"Serving docs on port {port} with upload endpoint at /upload")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()