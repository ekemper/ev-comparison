"""
Validate Carapis API response shape and check total Nissan Leaf inventory.
Budget: 1 API call.
"""

import json
import sys
sys.path.insert(0, ".")

from src import config
import requests

print("=== Carapis Validation (1 API call) ===\n")
print(f"Key configured: {'yes' if config.CARAPIS_API_KEY else 'NO'}")
print()

url = "https://api.carapis.com/v1/parsers/cargurus/search"
headers = {"Authorization": f"Bearer {config.CARAPIS_API_KEY}"}
payload = {
    "make": "Nissan",
    "model": "Leaf",
    "year_min": 2011,
    "year_max": 2025,
    "limit": 5,
    "offset": 0,
}

print(f"Request: POST {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

resp = requests.post(url, json=payload, headers=headers, timeout=30)
print(f"Status: {resp.status_code}")
print()

if resp.status_code != 200:
    print(f"ERROR: {resp.text[:500]}")
    # Try GET as fallback
    print("\n--- Trying GET instead ---")
    resp2 = requests.get(url, params=payload, headers=headers, timeout=30)
    print(f"GET Status: {resp2.status_code}")
    if resp2.status_code == 200:
        data = resp2.json()
        print(f"Top-level keys: {list(data.keys())}")
        print(json.dumps(data, indent=2, default=str)[:2000])
    else:
        print(f"GET Error: {resp2.text[:500]}")
    sys.exit(1)

data = resp.json()
print(f"Top-level keys: {list(data.keys())}")

# Navigate structure
inner = data.get("data", data)
if isinstance(inner, dict):
    print(f"data keys: {list(inner.keys())}")
    total = inner.get("total_count", inner.get("total", "?"))
    listings = inner.get("listings", inner.get("data", []))
    metadata = inner.get("search_metadata", {})
    print(f"Total count: {total}")
    print(f"Metadata: {json.dumps(metadata, indent=2, default=str)}")
    print(f"Listings in page: {len(listings)}")
else:
    listings = inner if isinstance(inner, list) else []
    total = len(listings)
    print(f"Data is a list with {len(listings)} items")

print()
if listings:
    print("=== First listing (full JSON) ===")
    print(json.dumps(listings[0], indent=2, default=str)[:2000])
