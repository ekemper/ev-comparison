"""
Try various Carapis URL patterns to find one that responds.
"""

import sys
sys.path.insert(0, ".")

from src import config
import requests

headers = {"Authorization": f"Bearer {config.CARAPIS_API_KEY}"}
params = {"source": "cargurus", "make": "Nissan", "model": "Leaf", "limit": 1}

urls = [
    "https://api.carapis.com/v2/listings",
    "https://api.carapis.com/listings",
    "https://carapis.com/api/v2/listings",
    "https://carapis.com/v2/listings",
    "https://www.carapis.com/api/v2/listings",
    "https://data.carapis.com/v2/listings",
]

for url in urls:
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        status = resp.status_code
        ct = resp.headers.get("content-type", "")
        body_preview = resp.text[:100] if "json" in ct or status == 200 else f"({ct})"
        print(f"  {status}  {url}  {body_preview}")
    except Exception as e:
        print(f"  ERR  {url}  {e}")
