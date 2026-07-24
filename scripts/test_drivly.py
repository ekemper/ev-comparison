"""
Driv.ly API test — shape validation and connectivity check.

Docs: https://docs.driv.ly/data/listings-search
Free tier (Develop): 100,000 credits/month, 2 RPS, no credit card required
Auth: Bearer token (or possibly open for basic read?)
Base URL: https://listings.vin
"""

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("DRIVLY_API_KEY", "").strip()
BASE_URL = "https://listings.vin"


def test_no_auth():
    """Try without auth — Driv.ly docs suggest some endpoints may be open."""
    print("=" * 60)
    print("TEST: No-auth probe (listings.vin)")
    print("=" * 60)

    params = {
        "vehicle.make": "Nissan",
        "vehicle.model": "Leaf",
        "limit": 2,
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        print(f"  Status: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('content-type')}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Top-level keys: {list(data.keys())}")
            print(f"  Total listings: {data.get('total')}")
            records = data.get("data", [])
            print(f"  Records returned: {len(records)}")
            if records:
                first = records[0]
                print(f"  First record keys: {list(first.keys())}")
                vehicle = first.get("vehicle", {})
                print(f"  VIN: {first.get('vin')}")
                print(f"  Year: {vehicle.get('year')}")
                print(f"  Make: {vehicle.get('make')}")
                print(f"  Model: {vehicle.get('model')}")
                print(f"  Trim: {vehicle.get('trim')}")
                retail = first.get("retailListing", {})
                print(f"  Price: {retail.get('price')}")
                print(f"  Miles: {retail.get('miles')}")
                print(f"  Dealer: {retail.get('dealerName')}")
                links = data.get("links", {})
                print(f"  Links: {links}")
            print("\n  No-auth access WORKS!")
        else:
            body = resp.text[:500]
            print(f"  Body: {body}")
    except Exception as e:
        print(f"  Error: {e}")


def test_with_key():
    """Test with Bearer token auth."""
    if not API_KEY:
        print("\n" + "=" * 60)
        print("SKIP: No DRIVLY_API_KEY in .env")
        print("Sign up at: https://landing.driv.ly/api")
        print("Then add key to .env as DRIVLY_API_KEY=<your_key>")
        print("=" * 60)
        return

    print("\n" + "=" * 60)
    print("TEST: Authenticated search (Nissan Leaf, limit=2)")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {
        "vehicle.make": "Nissan",
        "vehicle.model": "Leaf",
        "limit": 2,
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Top-level keys: {list(data.keys())}")
            print(f"  Total: {data.get('total')}")
            records = data.get("data", [])
            print(f"  Records returned: {len(records)}")
            if records:
                first = records[0]
                print(f"  First record keys: {list(first.keys())}")
                vehicle = first.get("vehicle", {})
                print(f"  VIN: {first.get('vin')}")
                print(f"  Year: {vehicle.get('year')}")
                print(f"  Make: {vehicle.get('make')}")
                print(f"  Model: {vehicle.get('model')}")
                print(f"  Trim: {vehicle.get('trim')}")
                print(f"  Body: {vehicle.get('bodyStyle')}")
                print(f"  Fuel: {vehicle.get('fuel')}")
                retail = first.get("retailListing", {})
                print(f"  Price: {retail.get('price')}")
                print(f"  Miles: {retail.get('miles')}")
                print(f"  Dealer: {retail.get('dealerName')}")
                print(f"  City: {retail.get('city')}")
                print(f"  State: {retail.get('state')}")
                links = data.get("links", {})
                print(f"  Links: {links}")
            print("\n  SUCCESS — authenticated access works!")
        else:
            body = resp.text[:500]
            print(f"  Body: {body}")
    except Exception as e:
        print(f"  Error: {e}")


def test_single_vin():
    """Test single-VIN lookup."""
    if not API_KEY:
        return

    print("\n" + "=" * 60)
    print("TEST: Single VIN lookup")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {API_KEY}"}
    test_vin = "1N4AZ1CP5LC310110"  # Known Nissan Leaf VIN
    url = f"{BASE_URL}/{test_vin}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Keys: {list(data.keys())}")
            vehicle = data.get("vehicle", {})
            print(f"  Year: {vehicle.get('year')}")
            print(f"  Make: {vehicle.get('make')}")
            print(f"  Model: {vehicle.get('model')}")
        else:
            print(f"  Body: {resp.text[:300]}")
    except Exception as e:
        print(f"  Error: {e}")


def test_prices_endpoint():
    """Test prices.vin endpoint."""
    if not API_KEY:
        return

    print("\n" + "=" * 60)
    print("TEST: prices.vin endpoint")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {API_KEY}"}
    test_vin = "1N4AZ1CP5LC310110"
    url = f"https://prices.vin/{test_vin}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Keys: {list(data.keys())}")
            print(f"  Retail: {data.get('retail')}")
            print(f"  TradeIn: {data.get('tradeIn')}")
        else:
            print(f"  Body: {resp.text[:300]}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    test_no_auth()
    test_with_key()
    test_single_vin()
    test_prices_endpoint()
