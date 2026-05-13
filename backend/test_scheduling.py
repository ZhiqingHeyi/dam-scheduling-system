import urllib.request
import json

data = json.dumps({
    "start_date": "2025/07/01",
    "deadline_date": "2026/12/31",
    "use_compression": False,
    "alpha": 0.5
}).encode()

req = urllib.request.Request(
    'http://localhost:8000/api/scheduling/run',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    r = urllib.request.urlopen(req, timeout=120)
    result = json.loads(r.read().decode())
    print(f"排仓结果: success={result.get('success')}")
    print(f"消息: {result.get('message')}")
    print(f"方案: {result.get('final_mode')}")
    print(f"完工日期: {result.get('final_end_date')}")
    print(f"排仓记录数: {len(result.get('schedule_data', []))}")
except Exception as e:
    print(f'Error: {e}')
    if hasattr(e, 'read'):
        body = e.read().decode()
        print(f'Detail: {body}')
