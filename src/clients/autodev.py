from __future__ import annotations

import logging
from typing import Any

import requests

from src import config

logger = logging.getLogger(__name__)

BASE_URL = "https://auto.dev/api"


class AutoDevClient:
    """Wrapper for the Auto.dev Listings API (v2)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.AUTODEV_API_KEY
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def search_listings(
        self,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        zip_code: str | None = None,
        radius: int | None = None,
        limit: int = 100,
        max_pages: int = 10,
        **filters: Any,
    ) -> list[dict]:
        """
        Search vehicle listings. Auto-paginates up to max_pages.
        Returns the combined list of raw listing dicts.
        """
        params: dict[str, Any] = {"limit": limit}
        if make is not None:
            params["make"] = make
        if model is not None:
            params["model"] = model
        if year is not None:
            params["year"] = year
        if year_min is not None:
            params["year_min"] = year_min
        if year_max is not None:
            params["year_max"] = year_max
        if zip_code is not None:
            params["zip"] = zip_code
        if radius is not None:
            params["radius"] = radius
        params.update(filters)

        all_listings: list[dict] = []

        for page in range(1, max_pages + 1):
            params["page"] = page
            data = self._get("/listings", params)
            records = data.get("records", data.get("data", []))
            if not records:
                break
            all_listings.extend(records)
            if len(records) < limit:
                break

        logger.info("Auto.dev: fetched %d listings", len(all_listings))
        return all_listings

    def decode_vin(self, vin: str) -> dict:
        """Decode a VIN to get vehicle specs."""
        return self._get(f"/vin/{vin}")
