"""
MarketCheck API test — shape validation and connectivity check.

Docs: https://docs.marketcheck.com/docs/get-started/api/authentication
Free tier: 500 calls/month, 5 RPS, 100-mile radius restriction
Auth: api_key query parameter
"""

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("MARKETCHECK_API_KEY", "").strip()

# The docs show api.marketcheck.com, but some older refs use mc-api.marketcheck.com
BASE_URLS = [
    "https://api.marketcheck.com/v2",
    "https://mc-api.marketcheck.com/v2",
]

def test_no_auth():
    """See what error we get without an API key."""
    print("=" * 60)
    print("TEST: No-auth probe (expect 401/403)")
    print("=" * 60)
    for base in BASE_URLS:
        url = f"{base}/search/car/active"
        params = {"make": "Nissan", "model": "Leaf", "rows": 1}
        try:
            resp = requests.get(url, params=params, timeout=15)
            print(f"\n  URL: {base}")
            print(f"  Status: {resp.status_code}")
            print(f"  Headers: {dict(resp.headers)}")
            body = resp.text[:500]
            print(f"  Body: {body}")
        except Exception as e:
            print(f"\n  URL: {base}")
            print(f"  Error: {e}")


def test_with_key():
    """Test with API key — shape validation."""
    if not API_KEY:
        print("\n" + "=" * 60)
        print("SKIP: No MARKETCHECK_API_KEY in .env")
        print("Sign up at: https://www.marketcheck.com/apis/pricing/")
        print("Then add key to .env as MARKETCHECK_API_KEY=<your_key>")
        print("=" * 60)
        return

    print("\n" + "=" * 60)
    print("TEST: Authenticated search (Nissan Leaf, rows=2)")
    print("=" * 60)

    for base in BASE_URLS:
        url = f"{base}/search/car/active"
        params = {
            "api_key": API_KEY,
            "make": "Nissan",
            "model": "Leaf",
            "rows": 2,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            print(f"\n  URL: {base}")
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  Top-level keys: {list(data.keys())}")
                print(f"  num_found: {data.get('num_found')}")
                listings = data.get("listings", [])
                print(f"  Listings returned: {len(listings)}")
                if listings:
                    first = listings[0]
                    print(f"  First listing keys: {list(first.keys())}")
                    print(f"  VIN: {first.get('vin')}")
                    print(f"  Year: {first.get('year')}")
                    print(f"  Make: {first.get('make')}")
                    print(f"  Model: {first.get('model')}")
                    print(f"  Trim: {first.get('trim')}")
                    print(f"  Price: {first.get('price')}")
                    print(f"  Miles: {first.get('miles')}")
                    print(f"  Exterior color: {first.get('exterior_color')}")
                    print(f"  Dealer city: {first.get('dealer', {}).get('city')}")
                    print(f"  Dealer state: {first.get('dealer', {}).get('state')}")
                print("\n  SUCCESS — this base URL works!")
                break
            else:
                body = resp.text[:300]
                print(f"  Body: {body}")
        except Exception as e:
            print(f"\n  URL: {base}")
            print(f"  Error: {e}")


def test_total_count():
    """Get total Nissan Leaf listings available."""
    if not API_KEY:
        return

    print("\n" + "=" * 60)
    print("TEST: Total count (national, no geo restriction)")
    print("=" * 60)

    url = f"https://api.marketcheck.com/v2/search/car/active"
    params = {
        "api_key": API_KEY,
        "make": "Nissan",
        "model": "Leaf",
        "rows": 0,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  num_found: {data.get('num_found')}")
        else:
            print(f"  Body: {resp.text[:300]}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    test_no_auth()
    test_with_key()
    test_total_count()
