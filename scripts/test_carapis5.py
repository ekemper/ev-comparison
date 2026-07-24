"""
Debug Carapis authentication. Try different auth methods.
"""

import sys
sys.path.insert(0, ".")

from src import config
import requests

key = config.CARAPIS_API_KEY
print(f"Key length: {len(key)}")
print(f"Key prefix: {key[:8]}...")
print()

url = "https://api.carapis.com/v2/listings"
params = {"source": "cargurus", "limit": 1}

# Method 1: Bearer token
print("1. Authorization: Bearer <key>")
resp = requests.get(url, params=params, headers={"Authorization": f"Bearer {key}"}, timeout=10)
print(f"   Status: {resp.status_code} | {resp.text[:200]}")
print()

# Method 2: x-api-key header
print("2. x-api-key: <key>")
resp = requests.get(url, params=params, headers={"x-api-key": key}, timeout=10)
print(f"   Status: {resp.status_code} | {resp.text[:200]}")
print()

# Method 3: api_key query param
print("3. ?api_key=<key>")
resp = requests.get(url, params={**params, "api_key": key}, timeout=10)
print(f"   Status: {resp.status_code} | {resp.text[:200]}")
print()

# Method 4: Try without any source param (maybe source isn't needed for some routes)
print("4. No source param, Bearer auth")
resp = requests.get(url, params={"limit": 1}, headers={"Authorization": f"Bearer {key}"}, timeout=10)
print(f"   Status: {resp.status_code} | {resp.text[:200]}")
