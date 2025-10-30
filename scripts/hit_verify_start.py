import json
import http.client

def hit(email: str):
    conn = http.client.HTTPConnection('localhost', 8004, timeout=5)
    payload = json.dumps({ 'identity': email })
    headers = { 'Content-Type': 'application/json' }
    conn.request('POST', '/api/users/verify/start', body=payload, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    print('status:', resp.status)
    print('body:', data.decode('utf-8'))
    conn.close()

if __name__ == '__main__':
    hit('krbucang@gmail.com')