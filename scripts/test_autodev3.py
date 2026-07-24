"""
Get total count of Nissan Leaf listings near Denver + national.
Budget: 2 API calls.
"""

import json
import sys
sys.path.insert(0, ".")

from src import config
import requests

url = "https://auto.dev/api/listings"
headers = {"Authorization": f"Bearer {config.AUTODEV_API_KEY}"}

# Call 1: Denver 200mi with total count
params_local = {
    "vehicle.make": "Nissan",
    "vehicle.model": "Leaf",
    "vehicle.year": "2011-2025",
    "zip": "80202",
    "distance": "200",
    "limit": "1",
    "includes": "total",
}

print("=== Denver 200mi radius ===")
resp = requests.get(url, params=params_local, headers=headers, timeout=30)
data = resp.json()
print(f"Top-level keys: {list(data.keys())}")
total_local = data.get("total", "not found")
print(f"Total Nissan Leaf listings (Denver 200mi): {total_local}")
print()

# Call 2: National (no zip filter)
params_national = {
    "vehicle.make": "Nissan",
    "vehicle.model": "Leaf",
    "vehicle.year": "2011-2025",
    "limit": "1",
    "includes": "total",
}

print("=== National (no location filter) ===")
resp2 = requests.get(url, params=params_national, headers=headers, timeout=30)
data2 = resp2.json()
total_national = data2.get("total", "not found")
print(f"Total Nissan Leaf listings (national): {total_national}")
print()

print("=== Summary ===")
print(f"Denver 200mi: {total_local} listings")
print(f"National:     {total_national} listings")
print()
if isinstance(total_local, int):
    pages_needed = (total_local + 99) // 100
    print(f"API calls to pull all Denver results (100/page): {pages_needed}")
if isinstance(total_national, int):
    pages_needed_nat = (total_national + 99) // 100
    print(f"API calls to pull all national results (100/page): {pages_needed_nat}")

print(f"\nTotal API calls used so far (including this script): 4")
