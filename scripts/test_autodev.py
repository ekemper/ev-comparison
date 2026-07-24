"""
Single API call to Auto.dev to validate response shape and check total Nissan Leaf inventory.
Budget: 1 API call.
"""

import json
import sys
sys.path.insert(0, ".")

from src import config
from src.clients.autodev import AutoDevClient

client = AutoDevClient()

print("=== Auto.dev Validation (1 API call) ===\n")
print(f"Key configured: {'yes' if config.AUTODEV_API_KEY else 'NO'}")
print()

# Single call: Nissan Leaf, all years, near Denver, limit=5
params = {
    "vehicle.make": "Nissan",
    "vehicle.model": "Leaf",
    "vehicle.year": "2011-2025",
    "zip": "80202",
    "distance": "200",
    "limit": "5",
    "page": "1",
}

print(f"Request: GET /listings")
print(f"Params: {json.dumps(params, indent=2)}")
print()

import requests

url = "https://auto.dev/api/listings"
headers = {"Authorization": f"Bearer {config.AUTODEV_API_KEY}"}
resp = requests.get(url, params=params, headers=headers, timeout=30)

print(f"Status: {resp.status_code}")
print(f"Headers: content-type={resp.headers.get('content-type')}")
print()

if resp.status_code != 200:
    print(f"ERROR: {resp.text[:500]}")
    sys.exit(1)

data = resp.json()

# Check top-level keys
print(f"Top-level keys: {list(data.keys())}")
total = data.get("total", data.get("totalCount", data.get("num_found", "unknown")))
print(f"Total results available: {total}")
print()

# Check listings
records = data.get("records", data.get("data", data.get("listings", [])))
print(f"Listings in this page: {len(records)}")
print()

if records:
    print("=== First listing (full JSON) ===")
    print(json.dumps(records[0], indent=2, default=str))
    print()
    if len(records) > 1:
        print("=== Second listing (keys only) ===")
        print(f"Keys: {list(records[1].keys())}")
