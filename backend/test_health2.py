import urllib.request
import urllib.error
import sys

url = 'http://127.0.0.1:8002/api/v1/health'
try:
    resp = urllib.request.urlopen(url, timeout=5)
    print(f"Status: {resp.status}")
    print(f"Body: {resp.read().decode()}")
except urllib.error.URLError as e:
    print(f"URL Error: {e.reason}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
