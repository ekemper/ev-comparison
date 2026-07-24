from __future__ import annotations

import logging
from typing import Any

import requests

from src import config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.carapis.com/v1/parsers/cargurus"


class CarapisClient:
    """Wrapper for the Carapis CarGurus parser API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.CARAPIS_API_KEY
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _post(self, path: str, payload: dict[str, Any] | None = None) -> dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.post(url, json=payload or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def search(
        self,
        make: str | None = None,
        model: str | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        zip_code: str | None = None,
        sort_by: str | None = None,
        limit: int = 100,
        max_pages: int = 10,
        **filters: Any,
    ) -> list[dict]:
        """
        Search CarGurus listings via Carapis. Auto-paginates up to max_pages.
        Returns the combined list of raw listing dicts.
        """
        payload: dict[str, Any] = {"limit": limit}
        if make is not None:
            payload["make"] = make
        if model is not None:
            payload["model"] = model
        if year_min is not None:
            payload["year_min"] = year_min
        if year_max is not None:
            payload["year_max"] = year_max
        if zip_code is not None:
            payload["zip"] = zip_code
        if sort_by is not None:
            payload["sort_by"] = sort_by
        payload.update(filters)

        all_listings: list[dict] = []

        for page in range(max_pages):
            payload["offset"] = page * limit
            data = self._post("/search", payload)
            inner = data.get("data", data)
            listings = inner.get("listings", [])
            if not listings:
                break
            all_listings.extend(listings)
            pagination = inner.get("search_metadata", {}).get("pagination", {})
            if not pagination.get("has_more", False):
                break

        logger.info("Carapis: fetched %d listings", len(all_listings))
        return all_listings

    def get_listing(self, listing_id: str) -> dict:
        """Fetch a single listing by Carapis ID."""
        return self._get(f"/listing/{listing_id}")
