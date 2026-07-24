"""
Probe Carapis API to find correct endpoints.
Budget: up to 3 calls (just probing different URLs).
"""

import json
import sys
sys.path.insert(0, ".")

from src import config
import requests

headers = {"Authorization": f"Bearer {config.CARAPIS_API_KEY}"}

# Try different URL patterns based on their docs
urls_to_try = [
    ("POST", "https://api.carapis.com/v1/cargurus/search", {"make": "Nissan", "model": "Leaf", "limit": 5}),
    ("GET", "https://api.carapis.com/v1/cargurus/search", {"make": "Nissan", "model": "Leaf", "limit": 5}),
    ("GET", "https://api.carapis.com/cargurus/search", {"make": "Nissan", "model": "Leaf", "limit": 5}),
    ("GET", "https://api.carapis.com/v1/listings", {"make": "Nissan", "model": "Leaf", "limit": 5}),
    ("POST", "https://api.carapis.com/parsers/cargurus/search", {"make": "Nissan", "model": "Leaf", "limit": 5}),
    ("GET", "https://api.carapis.com/parsers/cargurus/search", {"make": "Nissan", "model": "Leaf", "limit": 5}),
]

for method, url, payload in urls_to_try:
    print(f"{method} {url}")
    try:
        if method == "POST":
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
        else:
            resp = requests.get(url, params=payload, headers=headers, timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")
            print(f"  Preview: {json.dumps(data, default=str)[:300]}")
            print("\n  *** FOUND WORKING ENDPOINT ***")
            break
        elif resp.status_code in (401, 403):
            print(f"  Auth issue: {resp.text[:150]}")
        else:
            ct = resp.headers.get("content-type", "")
            if "json" in ct:
                print(f"  Body: {resp.text[:150]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()
