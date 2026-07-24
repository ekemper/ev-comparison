from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Source(str, Enum):
    MARKETCHECK = "marketcheck"
    AUTODEV = "autodev"
    DRIVLY = "drivly"
    CARAPIS = "carapis"


class SellerType(str, Enum):
    DEALER = "dealer"
    PRIVATE = "private"
    AUCTION = "auction"
    UNKNOWN = "unknown"


class Drivetrain(str, Enum):
    AWD = "awd"
    FWD = "fwd"
    RWD = "rwd"
    FOUR_WD = "4wd"
    UNKNOWN = "unknown"


class Condition(str, Enum):
    NEW = "new"
    CERTIFIED = "certified"
    USED = "used"
    FAIR = "fair"
    SALVAGE = "salvage"
    UNKNOWN = "unknown"


class FuelType(str, Enum):
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    PLUG_IN_HYBRID = "plug_in_hybrid"
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    OTHER = "other"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Listing(BaseModel):
    """Normalized vehicle listing — the core data model stored in MongoDB."""

    source: Source
    source_id: str
    search_run_id: str
    fetched_at: datetime = Field(default_factory=_utcnow)

    vin: str | None = None
    make: str
    model: str
    year: int
    trim: str | None = None

    drivetrain: Drivetrain | None = None
    fuel_type: FuelType | None = None
    body_style: str | None = None
    transmission: str | None = None
    engine: str | None = None
    exterior_color: str | None = None
    interior_color: str | None = None

    battery_capacity_kwh: float | None = None
    range_miles: int | None = None

    price: float | None = None
    mileage: int | None = None
    condition: Condition | None = None
    seller_type: SellerType | None = None
    days_on_market: int | None = None

    city: str | None = None
    state: str | None = None
    zip: str | None = None

    url: str | None = None
    image_url: str | None = None
    dealer_name: str | None = None

    raw: dict[str, Any] = Field(default_factory=dict)

    def to_mongo(self) -> dict:
        """Serialize to a MongoDB-ready dict. Enums become their string values."""
        d = self.model_dump(mode="json")
        d["fetched_at"] = self.fetched_at
        return d

    @classmethod
    def from_mongo(cls, doc: dict) -> Listing:
        """Deserialize a MongoDB document back into a Listing."""
        doc.pop("_id", None)
        return cls.model_validate(doc)


class SearchParams(BaseModel):
    make: str
    model: str
    year_min: int | None = None
    year_max: int | None = None
    zip: str | None = None
    radius: int | None = None


class SourceResult(BaseModel):
    count: int = 0
    status: str = "pending"
    error: str | None = None


class SearchRun(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    params: SearchParams
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = None
    sources: dict[str, SourceResult] = Field(default_factory=dict)
    total_listings: int = 0

    def to_mongo(self) -> dict:
        d = self.model_dump(mode="json")
        d["_id"] = d.pop("id")
        d["started_at"] = self.started_at
        if self.completed_at:
            d["completed_at"] = self.completed_at
        return d

    @classmethod
    def from_mongo(cls, doc: dict) -> SearchRun:
        doc["id"] = doc.pop("_id")
        return cls.model_validate(doc)


class SearchResult(BaseModel):
    run_id: str
    params: SearchParams
    total_listings: int
    per_source: dict[str, int]
    errors: dict[str, str]
