from __future__ import annotations

import logging
from typing import Any

import requests

from src import config

logger = logging.getLogger(__name__)

LISTINGS_BASE = "https://listings.vin"


class DrivlyClient:
    """Wrapper for the Driv.ly Listings API (listings.vin)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.DRIVLY_API_KEY
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict:
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_listings(
        self,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        limit: int = 100,
        max_pages: int = 10,
        **filters: Any,
    ) -> list[dict]:
        """
        Search vehicle listings on listings.vin. Auto-paginates up to max_pages.
        Returns the combined list of raw listing dicts.
        """
        params: dict[str, Any] = {"limit": limit}
        if make is not None:
            params["vehicle.make"] = make
        if model is not None:
            params["vehicle.model"] = model
        if year is not None:
            params["vehicle.year"] = year
        if year_min is not None:
            params["vehicle.year_min"] = year_min
        if year_max is not None:
            params["vehicle.year_max"] = year_max
        params.update(filters)

        all_listings: list[dict] = []

        for page in range(1, max_pages + 1):
            params["page"] = page
            data = self._get(LISTINGS_BASE, params)
            records = data.get("data", [])
            if not records:
                break
            all_listings.extend(records)
            links = data.get("links", {})
            if not links.get("next"):
                break

        logger.info("Driv.ly: fetched %d listings", len(all_listings))
        return all_listings

    def get_vin(self, vin: str) -> dict:
        """Look up a single vehicle by VIN."""
        return self._get(f"{LISTINGS_BASE}/{vin}")

    def get_prices(self, vin: str) -> dict:
        """Get aggregated valuations (KBB, Edmunds, NADA, BlackBook, MMR)."""
        return self._get(f"https://prices.vin/{vin}")
