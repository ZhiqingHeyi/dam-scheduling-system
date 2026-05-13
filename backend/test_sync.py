import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8000/api/database/sync-data',
    data=b'{}',
    headers={'Content-Type': 'application/json'}
)

try:
    r = urllib.request.urlopen(req, timeout=30)
    print(r.read().decode())
except Exception as e:
    print(f'Error: {e}')
    if hasattr(e, 'read'):
        body = e.read().decode()
        print(f'Detail: {body}')
