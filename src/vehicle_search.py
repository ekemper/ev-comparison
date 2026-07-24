from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.clients.autodev import AutoDevClient
from src.clients.carapis import CarapisClient
from src.clients.drivly import DrivlyClient
from src.clients.marketcheck import MarketCheckClient
from src.models import (
    Condition,
    Drivetrain,
    FuelType,
    Listing,
    SearchParams,
    SearchResult,
    SearchRun,
    SellerType,
    Source,
    SourceResult,
)
from src.store import ListingStore

logger = logging.getLogger(__name__)

_DRIVETRAIN_MAP: dict[str, Drivetrain] = {
    "fwd": Drivetrain.FWD,
    "rwd": Drivetrain.RWD,
    "awd": Drivetrain.AWD,
    "4wd": Drivetrain.FOUR_WD,
    "4x4": Drivetrain.FOUR_WD,
    "all wheel drive": Drivetrain.AWD,
    "front wheel drive": Drivetrain.FWD,
    "rear wheel drive": Drivetrain.RWD,
    "four wheel drive": Drivetrain.FOUR_WD,
}


def _parse_drivetrain(val: str | None) -> Drivetrain | None:
    if not val:
        return None
    return _DRIVETRAIN_MAP.get(val.strip().lower(), Drivetrain.UNKNOWN)


def _parse_fuel_type(
    fuel: str | None = None,
    powertrain: str | None = None,
    engine: str | None = None,
) -> FuelType | None:
    combined = " ".join(filter(None, [fuel, powertrain, engine])).lower()
    if not combined.strip():
        return None
    if "bev" in combined or combined.startswith("electric") or "electric motor" in combined:
        return FuelType.ELECTRIC
    if "phev" in combined or "plug-in hybrid" in combined or "plug_in_hybrid" in combined:
        return FuelType.PLUG_IN_HYBRID
    if "hev" in combined or "mhev" in combined or "hybrid" in combined:
        return FuelType.HYBRID
    if "diesel" in combined:
        return FuelType.DIESEL
    return FuelType.GASOLINE


def _parse_seller_type(val: str | None) -> SellerType | None:
    if not val:
        return None
    v = val.strip().lower()
    if v == "dealer":
        return SellerType.DEALER
    if v in ("private", "fsbo"):
        return SellerType.PRIVATE
    if v == "auction":
        return SellerType.AUCTION
    return SellerType.UNKNOWN


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


def _safe_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _first(lst: list | None) -> str | None:
    if lst and len(lst) > 0:
        return str(lst[0])
    return None


class VehicleSearch:
    """
    Aggregation layer: fan out to all sources, normalize to Listing models,
    store in MongoDB, return a summary.
    """

    def __init__(self, store: ListingStore | None = None):
        self.mc = MarketCheckClient()
        self.autodev = AutoDevClient()
        self.drivly = DrivlyClient()
        self.carapis = CarapisClient()
        self.store = store or ListingStore()

    def search(
        self,
        make: str,
        model: str,
        year_min: int | None = None,
        year_max: int | None = None,
        zip_code: str | None = None,
        radius: int | None = None,
        sources: list[str] | None = None,
        max_pages: int = 10,
    ) -> SearchResult:
        params = SearchParams(
            make=make,
            model=model,
            year_min=year_min,
            year_max=year_max,
            zip=zip_code,
            radius=radius,
        )
        run = SearchRun(params=params)
        self.store.save_search_run(run)

        enabled = sources or [s.value for s in Source]
        fetchers: dict[str, tuple] = {
            Source.MARKETCHECK.value: (self._fetch_marketcheck, params),
            Source.AUTODEV.value: (self._fetch_autodev, params),
            Source.DRIVLY.value: (self._fetch_drivly, params),
            Source.CARAPIS.value: (self._fetch_carapis, params),
        }

        total = 0
        per_source: dict[str, int] = {}
        errors: dict[str, str] = {}

        for source_name in enabled:
            if source_name not in fetchers:
                continue
            fetch_fn, p = fetchers[source_name]
            run.sources[source_name] = SourceResult(status="pending")

            try:
                raw_listings = fetch_fn(p, max_pages=max_pages)
                listings = []
                for raw in raw_listings:
                    try:
                        listing = self._normalize(source_name, raw, run.id)
                        listings.append(listing)
                    except Exception as e:
                        logger.debug("Normalization error for %s: %s", source_name, e)

                if listings:
                    result = self.store.upsert_many(listings)
                    count = result["inserted"] + result["updated"]
                else:
                    count = 0

                per_source[source_name] = count
                total += count
                run.sources[source_name] = SourceResult(count=count, status="ok")

            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                logger.error("Error fetching from %s: %s", source_name, msg)
                errors[source_name] = msg
                per_source[source_name] = 0
                run.sources[source_name] = SourceResult(status="error", error=msg)

        run.completed_at = datetime.now(timezone.utc)
        run.total_listings = total
        self.store.save_search_run(run)

        return SearchResult(
            run_id=run.id,
            params=params,
            total_listings=total,
            per_source=per_source,
            errors=errors,
        )

    # ── Fetchers ──

    def _fetch_marketcheck(
        self, params: SearchParams, max_pages: int = 10
    ) -> list[dict]:
        return self.mc.search_active(
            make=params.make,
            model=params.model,
            year_min=params.year_min,
            year_max=params.year_max,
            zip_code=params.zip,
            radius=params.radius,
            max_pages=max_pages,
        )

    def _fetch_autodev(
        self, params: SearchParams, max_pages: int = 10
    ) -> list[dict]:
        return self.autodev.search_listings(
            make=params.make,
            model=params.model,
            year_min=params.year_min,
            year_max=params.year_max,
            zip_code=params.zip,
            radius=params.radius,
            max_pages=max_pages,
        )

    def _fetch_drivly(
        self, params: SearchParams, max_pages: int = 10
    ) -> list[dict]:
        return self.drivly.get_listings(
            make=params.make,
            model=params.model,
            year_min=params.year_min,
            year_max=params.year_max,
            max_pages=max_pages,
        )

    def _fetch_carapis(
        self, params: SearchParams, max_pages: int = 10
    ) -> list[dict]:
        return self.carapis.search(
            make=params.make,
            model=params.model,
            year_min=params.year_min,
            year_max=params.year_max,
            max_pages=max_pages,
        )

    # ── Normalization ──

    def _normalize(self, source: str, raw: dict, run_id: str) -> Listing:
        if source == Source.MARKETCHECK.value:
            return self._normalize_marketcheck(raw, run_id)
        if source == Source.AUTODEV.value:
            return self._normalize_autodev(raw, run_id)
        if source == Source.DRIVLY.value:
            return self._normalize_drivly(raw, run_id)
        if source == Source.CARAPIS.value:
            return self._normalize_carapis(raw, run_id)
        raise ValueError(f"Unknown source: {source}")

    def _normalize_marketcheck(self, raw: dict, run_id: str) -> Listing:
        build = raw.get("build", {})
        dealer = raw.get("dealer", {})
        media = raw.get("media", {})

        inventory_type = _safe_str(raw.get("inventory_type"))
        is_certified = raw.get("is_certified")
        if inventory_type and inventory_type.lower() == "new":
            condition = Condition.NEW
        elif is_certified == 1:
            condition = Condition.CERTIFIED
        else:
            condition = Condition.USED

        return Listing(
            source=Source.MARKETCHECK,
            source_id=str(raw["id"]),
            search_run_id=run_id,
            vin=_safe_str(raw.get("vin")),
            make=build.get("make", ""),
            model=build.get("model", ""),
            year=int(build.get("year", 0)),
            trim=_safe_str(build.get("trim")),
            drivetrain=_parse_drivetrain(build.get("drivetrain")),
            fuel_type=_parse_fuel_type(
                fuel=build.get("fuel_type"),
                powertrain=build.get("powertrain_type"),
                engine=build.get("engine"),
            ),
            body_style=_safe_str(build.get("body_type", "")).lower() if build.get("body_type") else None,
            transmission=_safe_str(build.get("transmission")),
            engine=_safe_str(build.get("engine")),
            exterior_color=_safe_str(raw.get("base_ext_color") or raw.get("exterior_color")),
            interior_color=_safe_str(raw.get("base_int_color") or raw.get("interior_color")),
            price=_safe_float(raw.get("price")),
            mileage=_safe_int(raw.get("miles")),
            condition=condition,
            seller_type=_parse_seller_type(raw.get("seller_type")),
            days_on_market=_safe_int(raw.get("dom_active")),
            city=_safe_str(dealer.get("city")),
            state=_safe_str(dealer.get("state")),
            zip=_safe_str(dealer.get("zip")),
            url=_safe_str(raw.get("vdp_url")),
            image_url=_first(media.get("photo_links") or media.get("photo_links_cached")),
            dealer_name=_safe_str(dealer.get("name")),
            raw=raw,
        )

    def _normalize_autodev(self, raw: dict, run_id: str) -> Listing:
        vehicle = raw.get("vehicle", {})
        retail = raw.get("retailListing", {})
        wholesale = raw.get("wholesaleListing", {})

        used = retail.get("used", True)
        cpo = retail.get("cpo", False)
        if not used:
            condition = Condition.NEW
        elif cpo:
            condition = Condition.CERTIFIED
        else:
            condition = Condition.USED

        if wholesale and wholesale.get("auction"):
            seller_type = SellerType.AUCTION
        else:
            seller_type = SellerType.DEALER

        price = _safe_float(retail.get("price"))
        mileage = _safe_int(retail.get("miles") or wholesale.get("miles"))

        return Listing(
            source=Source.AUTODEV,
            source_id=str(raw.get("vin", raw.get("@id", ""))),
            search_run_id=run_id,
            vin=_safe_str(raw.get("vin")),
            make=vehicle.get("make", ""),
            model=vehicle.get("model", ""),
            year=int(vehicle.get("year", 0)),
            trim=_safe_str(vehicle.get("trim")),
            drivetrain=_parse_drivetrain(vehicle.get("drivetrain")),
            fuel_type=_parse_fuel_type(
                fuel=vehicle.get("fuel"),
                engine=vehicle.get("engine"),
            ),
            transmission=_safe_str(vehicle.get("transmission")),
            engine=_safe_str(vehicle.get("engine")),
            price=price,
            mileage=mileage,
            condition=condition,
            seller_type=seller_type,
            city=_safe_str(retail.get("city")),
            state=_safe_str(retail.get("state")),
            zip=_safe_str(retail.get("zip")),
            url=_safe_str(retail.get("vdp")),
            image_url=_safe_str(retail.get("primaryImage")),
            dealer_name=_safe_str(retail.get("dealer")),
            raw=raw,
        )

    def _normalize_drivly(self, raw: dict, run_id: str) -> Listing:
        vehicle = raw.get("vehicle", {})
        retail = raw.get("retailListing", {})
        wholesale = raw.get("wholesaleListing", {})

        used = retail.get("used", True)
        cpo = retail.get("cpo", False)
        if not used:
            condition = Condition.NEW
        elif cpo:
            condition = Condition.CERTIFIED
        else:
            condition = Condition.USED

        if wholesale and wholesale.get("auction"):
            seller_type = SellerType.AUCTION
        else:
            seller_type = SellerType.DEALER

        body = _safe_str(vehicle.get("bodyStyle"))

        return Listing(
            source=Source.DRIVLY,
            source_id=str(raw.get("vin", "")),
            search_run_id=run_id,
            vin=_safe_str(raw.get("vin")),
            make=vehicle.get("make", ""),
            model=vehicle.get("model", ""),
            year=int(vehicle.get("year", 0)),
            trim=_safe_str(vehicle.get("trim")),
            drivetrain=_parse_drivetrain(vehicle.get("drivetrain")),
            fuel_type=_parse_fuel_type(
                fuel=vehicle.get("fuel"),
                engine=vehicle.get("engine"),
            ),
            body_style=body.lower() if body else None,
            transmission=_safe_str(vehicle.get("transmission")),
            engine=_safe_str(vehicle.get("engine")),
            exterior_color=_safe_str(vehicle.get("exteriorColor")),
            interior_color=_safe_str(vehicle.get("interiorColor")),
            price=_safe_float(retail.get("price")),
            mileage=_safe_int(retail.get("miles")),
            condition=condition,
            seller_type=seller_type,
            city=_safe_str(retail.get("city")),
            state=_safe_str(retail.get("state")),
            url=_safe_str(raw.get("url")),
            image_url=_safe_str(retail.get("primaryImage")),
            dealer_name=_safe_str(retail.get("dealer")),
            raw=raw,
        )

    def _normalize_carapis(self, raw: dict, run_id: str) -> Listing:
        specs = raw.get("specifications", {})
        location = raw.get("location", {})
        seller = raw.get("seller", {})
        price_obj = raw.get("price", {})
        images = raw.get("images", [])

        title = raw.get("title", "")
        parts = title.split() if title else []
        make = parts[0] if len(parts) >= 1 else ""
        model = parts[1] if len(parts) >= 2 else ""
        trim = " ".join(parts[2:]) if len(parts) >= 3 else None

        if seller.get("certified"):
            condition = Condition.CERTIFIED
        else:
            condition = Condition.USED

        return Listing(
            source=Source.CARAPIS,
            source_id=str(raw.get("id", "")),
            search_run_id=run_id,
            vin=_safe_str(specs.get("vin")),
            make=make,
            model=model,
            year=int(specs.get("year", 0)),
            trim=trim,
            drivetrain=_parse_drivetrain(specs.get("drivetrain")),
            fuel_type=_parse_fuel_type(fuel=specs.get("fuel_type")),
            transmission=_safe_str(specs.get("transmission")),
            engine=_safe_str(specs.get("engine_size")),
            price=_safe_float(price_obj.get("amount")),
            mileage=_safe_int(specs.get("mileage")),
            condition=condition,
            seller_type=_parse_seller_type(seller.get("type")),
            city=_safe_str(location.get("city")),
            state=_safe_str(location.get("state")),
            zip=_safe_str(location.get("postal_code")),
            url=_safe_str(raw.get("url")),
            image_url=_first(images),
            dealer_name=_safe_str(seller.get("name")),
            raw=raw,
        )
