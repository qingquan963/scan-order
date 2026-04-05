import urllib.request
import sys

try:
    resp = urllib.request.urlopen('http://127.0.0.1:8002/api/v1/health', timeout=5)
    print(f"Status: {resp.status}")
    print(f"Body: {resp.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
