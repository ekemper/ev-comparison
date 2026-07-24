from __future__ import annotations

import logging
from typing import Any

import requests

from src import config

logger = logging.getLogger(__name__)

BASE_URL = "https://mc-api.marketcheck.com/v2"


class MarketCheckClient:
    """Wrapper for the MarketCheck Cars API (v2)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.MARKETCHECK_API_KEY
        self.session = requests.Session()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        params = params or {}
        params["api_key"] = self.api_key
        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def search_active(
        self,
        make: str,
        model: str,
        year: int | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        zip_code: str | None = None,
        radius: int | None = None,
        rows: int = 50,
        max_pages: int = 10,
        **filters: Any,
    ) -> list[dict]:
        """
        Search active inventory. Auto-paginates up to max_pages.
        Returns the combined list of raw listing dicts.
        """
        params: dict[str, Any] = {
            "make": make,
            "model": model,
            "rows": rows,
        }
        if year is not None:
            params["year"] = year
        if year_min is not None:
            params["year_range_min"] = year_min
        if year_max is not None:
            params["year_range_max"] = year_max
        if zip_code is not None:
            params["zip"] = zip_code
        if radius is not None:
            params["radius"] = radius
        params.update(filters)

        all_listings: list[dict] = []
        start = 0

        for _ in range(max_pages):
            params["start"] = start
            data = self._get("/search/car/active", params)
            listings = data.get("listings", [])
            if not listings:
                break
            all_listings.extend(listings)
            num_found = data.get("num_found", 0)
            start += rows
            if start >= num_found:
                break

        logger.info("MarketCheck: fetched %d listings", len(all_listings))
        return all_listings

    def get_listing(self, listing_id: str) -> dict:
        """Fetch a single listing by MarketCheck ID."""
        return self._get(f"/listing/{listing_id}")

    def get_vin(self, vin: str) -> dict:
        """Look up a vehicle by VIN."""
        return self._get(f"/vin/{vin}/active")
