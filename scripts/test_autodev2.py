"""
Check pagination info from the first call. NO additional API call needed.
Re-run the same call but print the links object.
Budget: 1 API call.
"""

import json
import sys
sys.path.insert(0, ".")

from src import config
import requests

url = "https://auto.dev/api/listings"
headers = {"Authorization": f"Bearer {config.AUTODEV_API_KEY}"}
params = {
    "vehicle.make": "Nissan",
    "vehicle.model": "Leaf",
    "vehicle.year": "2011-2025",
    "zip": "80202",
    "distance": "200",
    "limit": "5",
    "page": "1",
}

resp = requests.get(url, params=params, headers=headers, timeout=30)
data = resp.json()

print("=== Links object ===")
print(json.dumps(data.get("links", {}), indent=2))
print()

print("=== Data count in this page ===")
print(f"{len(data.get('data', []))} listings")
print()

# Also check if there's a facets mode to get total count
print("=== All top-level keys and their types ===")
for k, v in data.items():
    if isinstance(v, list):
        print(f"  {k}: list ({len(v)} items)")
    elif isinstance(v, dict):
        print(f"  {k}: dict (keys: {list(v.keys())[:10]})")
    else:
        print(f"  {k}: {type(v).__name__} = {v}")
