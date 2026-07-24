"""
Validate Carapis v2 API with correct endpoint.
Budget: 1 API call.
"""

import json
import sys
sys.path.insert(0, ".")

from src import config
import requests

print("=== Carapis v2 Validation (1 API call) ===\n")

url = "https://api.carapis.com/v2/listings"
headers = {"Authorization": f"Bearer {config.CARAPIS_API_KEY}"}
params = {
    "source": "cargurus",
    "make": "Nissan",
    "model": "Leaf",
    "year_min": 2011,
    "year_max": 2025,
    "limit": 5,
}

print(f"Request: GET {url}")
print(f"Params: {json.dumps(params, indent=2)}")
print()

resp = requests.get(url, params=params, headers=headers, timeout=30)
print(f"Status: {resp.status_code}")
print()

if resp.status_code != 200:
    print(f"Error: {resp.text[:500]}")
    sys.exit(1)

data = resp.json()
print(f"Top-level keys: {list(data.keys())}")

total = data.get("total", data.get("total_count", "?"))
print(f"Total available: {total}")

listings = data.get("data", data.get("listings", []))
print(f"Listings in page: {len(listings)}")
print()

if listings:
    print("=== First listing (full JSON) ===")
    print(json.dumps(listings[0], indent=2, default=str)[:2000])
