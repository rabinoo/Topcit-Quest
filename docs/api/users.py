from lib.users.register import handler as register_handler
from lib.users.login import handler as login_handler
from lib.users.verify import handler as verify_handler
from lib.users.verify.start import handler as verify_start_handler
from lib.users.me import handler as me_handler
from lib.users.progress import handler as progress_handler

def handler(request):
    route = None
    # Try to read from query params first
    try:
        if hasattr(request, 'args') and request.args:
            route = request.args.get('route')
    except Exception:
        pass
    if not route:
        try:
            if hasattr(request, 'query') and request.query:
                route = request.query.get('route')
        except Exception:
            pass

    # Fallback: infer from path if present
    if not route:
        try:
            path = getattr(request, 'path', '') or getattr(request, 'url', '')
            if path and '/api/users/' in path:
                route = path.split('/api/users/', 1)[1]
        except Exception:
            route = None

    route = (route or '').strip('/').lower()

    try:
        if route == 'register':
            return register_handler(request)
        if route == 'login':
            return login_handler(request)
        if route in ('verify',):
            return verify_handler(request)
        if route in ('verify-start', 'verify/start'):
            return verify_start_handler(request)
        if route == 'me':
            return me_handler(request)
        if route == 'progress':
            return progress_handler(request)

        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': '{"error":"Unknown users route"}'
        }
    except Exception:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': '{"error":"Internal server error"}'
        }