"""
Pull all Nissan Leaf listings nationally from Auto.dev.
Saves raw JSON to data/nissan_leaf_raw.json.
Expected: ~765 listings. Free tier appears to cap at 20/page = ~39 calls needed.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from src import config
import requests

url = "https://auto.dev/api/listings"
headers = {"Authorization": f"Bearer {config.AUTODEV_API_KEY}"}

base_params = {
    "vehicle.make": "Nissan",
    "vehicle.model": "Leaf",
    "vehicle.year": "2011-2025",
    "limit": "100",
    "includes": "total",
}

all_listings = []
page = 1
total = None
max_pages = 50  # safety cap

print("=== Pulling all Nissan Leaf listings (national) ===\n")

while page <= max_pages:
    params = {**base_params, "page": str(page)}
    print(f"  Page {page}...", end=" ", flush=True)

    resp = requests.get(url, params=params, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"ERROR {resp.status_code}: {resp.text[:200]}")
        break

    data = resp.json()

    if total is None:
        total = data.get("total", "?")
        print(f"(total: {total})", end=" ")

    records = data.get("data", [])
    print(f"got {len(records)}")

    if not records:
        break

    all_listings.extend(records)

    if len(all_listings) >= total:
        break

    page += 1
    time.sleep(0.25)

print(f"\n=== Done ===")
print(f"Total listings pulled: {len(all_listings)}")
print(f"API calls used this run: {page}")

# Deduplicate by VIN
seen_vins = set()
unique = []
for item in all_listings:
    vin = item.get("vin", "")
    if vin and vin in seen_vins:
        continue
    seen_vins.add(vin)
    unique.append(item)

print(f"Unique listings (by VIN): {len(unique)}")

# Save to file
out_dir = Path("data")
out_dir.mkdir(exist_ok=True)
out_path = out_dir / "nissan_leaf_raw.json"
with open(out_path, "w") as f:
    json.dump({
        "source": "autodev",
        "query": base_params,
        "total_available": total,
        "count": len(unique),
        "api_calls_used": page,
        "listings": unique,
    }, f, indent=2, default=str)

print(f"Saved to: {out_path}")
print(f"File size: {out_path.stat().st_size / 1024:.0f} KB")
