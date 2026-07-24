# API Clients — Plan

## Summary / goal

Build Python utility modules that connect to each of the four Tier 1 vehicle listing APIs (MarketCheck, Auto.dev, Driv.ly, Carapis/CarGurus). Each client wraps its API faithfully with auto-pagination, loads secrets from a `.env` file, and is independently usable. A `VehicleSearch` aggregation class provides a single entry point: specify car parameters once, fan out to all sources, and store the combined results in MongoDB with source tracking and deduplication. A setup README walks the user through account creation and API key acquisition for each service with direct links to every portal.

## Scope

**In scope:**
1. Four bespoke API client modules — one per service
2. Shared config module that loads `.env` via `python-dotenv`
3. `.env.example` template with all required keys documented
4. `SETUP.md` with step-by-step account creation instructions and portal links for all four services
5. `VehicleSearch` aggregation class — single entry point that fans out to all clients, normalizes results to a common schema, and stores them in MongoDB
6. MongoDB storage layer with deduplication and source tracking
7. A lightweight CLI entry point (`main.py`) to smoke-test each client and run an aggregated search
8. `uv` as the package manager (`pyproject.toml`)

**Out of scope:**
- ML model training pipeline (separate plan)
- Rate limiting / retry logic beyond basic error handling
- Async / concurrent fetching
- Web UI

**Dependencies:**
- Python 3.11+
- Docker (for MongoDB via `docker-compose.yml`)
- Network access to each API (requires valid keys)
- `uv` installed locally

## Approach

Single phase — all four clients are independent of each other and can be implemented sequentially in one conversation.

### Directory layout

```
ev-comparison/
├── pyproject.toml
├── docker-compose.yml       # MongoDB container
├── .env.example
├── .gitignore
├── SETUP.md
├── src/
│   ├── __init__.py
│   ├── config.py            # loads .env, exposes API keys + mongo URI
│   ├── models.py            # Pydantic data models (Listing, SearchRun, etc.)
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── marketcheck.py
│   │   ├── autodev.py
│   │   ├── drivly.py
│   │   └── carapis.py
│   ├── store.py             # MongoDB storage layer
│   ├── vehicle_search.py    # VehicleSearch aggregation class
│   └── main.py              # CLI smoke test + aggregated search
```

### Module design

**`src/config.py`** — Single module that loads `.env` via `python-dotenv` and exposes typed config:
- `MARKETCHECK_API_KEY`
- `MARKETCHECK_CLIENT_SECRET` (for OAuth if needed)
- `AUTODEV_API_KEY`
- `DRIVLY_API_KEY`
- `CARAPIS_API_KEY`

Also exposes:
- `MONGODB_URI` (default: `mongodb://localhost:27017`)
- `MONGODB_DB_NAME` (default: `ev_comparison`)

Raises `ValueError` at import time if a required API key is missing, with a message pointing to `SETUP.md`.

**Each client module** follows the same pattern:
1. A class named after the service (e.g., `MarketCheckClient`)
2. Constructor takes the API key (defaults to loading from config)
3. Methods map to the API's endpoints, returning parsed JSON (dicts/lists)
4. Auto-pagination: methods that return lists iterate through all pages internally and return the complete result set
5. Raises `requests.HTTPError` on non-2xx responses with the response body attached

### Client details

**`MarketCheckClient`**
- Auth: API key as query param (`api_key=`) or OAuth 2.0 bearer token
- Base URL: `https://mc-api.marketcheck.com/v2`
- Key methods:
  - `search_active(make, model, year=None, zip=None, radius=None, rows=50, **filters) -> list[dict]`
  - `get_listing(id) -> dict`
  - `get_vin(vin) -> dict`
- Pagination: `start` param offset, iterate until `listings` is empty or `num_found` reached

**`AutoDevClient`**
- Auth: Bearer token in `Authorization` header
- Base URL: `https://api.auto.dev`
- Key methods:
  - `search_listings(make=None, model=None, year=None, zip=None, radius=None, page=1, **filters) -> list[dict]`
  - `decode_vin(vin) -> dict`
- Pagination: `page` param, iterate until results are empty

**`DrivlyClient`**
- Auth: Bearer token in `Authorization` header
- Base URL: `https://api.driv.ly`
- Key methods:
  - `get_listings(make=None, model=None, year=None, zip=None, **filters) -> list[dict]`
  - `get_vin(vin) -> dict`
  - `get_prices(vin) -> dict` — returns aggregated KBB/Edmunds/NADA/BlackBook/MMR valuations
- Pagination: follows API's pagination convention (cursor or offset based per endpoint)

**`CarapisClient`**
- Auth: Bearer token in `Authorization` header
- Base URL: `https://api.carapis.com/v1/parsers/cargurus`
- Key methods:
  - `search(make=None, model=None, year_min=None, year_max=None, zip=None, sort_by=None, **filters) -> list[dict]`
  - `get_listing(id) -> dict`
- Pagination: `page` param, iterate until no more results

### Data models

**`src/models.py`** — Pydantic models that define the normalized data shape. This file is the single source of truth for the listing schema. Every other module (`store.py`, `vehicle_search.py`, `main.py`) imports from here.

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


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
    CERTIFIED = "certified"  # CPO
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


class Listing(BaseModel):
    """Normalized vehicle listing — the core data model stored in MongoDB."""

    # Identity & provenance
    source: Source
    source_id: str
    search_run_id: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    # Vehicle identification
    vin: str | None = None
    make: str
    model: str
    year: int
    trim: str | None = None

    # Specs
    drivetrain: Drivetrain | None = None
    fuel_type: FuelType | None = None
    body_style: str | None = None           # sedan, suv, truck, etc.
    transmission: str | None = None         # automatic, manual
    engine: str | None = None               # "electric motor", "2.0L I4", etc.
    exterior_color: str | None = None
    interior_color: str | None = None

    # EV-specific
    battery_capacity_kwh: float | None = None
    range_miles: int | None = None

    # Pricing & market
    price: float | None = None
    mileage: int | None = None
    condition: Condition | None = None
    seller_type: SellerType | None = None
    days_on_market: int | None = None

    # Location
    city: str | None = None
    state: str | None = None
    zip: str | None = None

    # Listing metadata
    url: str | None = None                  # link back to the listing
    image_url: str | None = None
    dealer_name: str | None = None

    # Raw payload preserved for debugging / future feature extraction
    raw: dict[str, Any] = Field(default_factory=dict)

    def to_mongo(self) -> dict:
        """Serialize to a MongoDB-ready dict. Enums become their string values."""
        d = self.model_dump(mode="json")
        d["fetched_at"] = self.fetched_at  # keep as datetime, not ISO string
        return d

    @classmethod
    def from_mongo(cls, doc: dict) -> "Listing":
        """Deserialize a MongoDB document back into a Listing."""
        doc.pop("_id", None)
        return cls.model_validate(doc)


class SearchParams(BaseModel):
    """Parameters for a vehicle search."""
    make: str
    model: str
    year_min: int | None = None
    year_max: int | None = None
    zip: str | None = None
    radius: int | None = None


class SourceResult(BaseModel):
    """Per-source outcome within a search run."""
    count: int = 0
    status: str = "pending"     # "ok" | "error" | "skipped" | "pending"
    error: str | None = None


class SearchRun(BaseModel):
    """Metadata for a single aggregated search execution."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    params: SearchParams
    started_at: datetime = Field(default_factory=datetime.utcnow)
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
    def from_mongo(cls, doc: dict) -> "SearchRun":
        doc["id"] = doc.pop("_id")
        return cls.model_validate(doc)


class SearchResult(BaseModel):
    """Returned to the caller after VehicleSearch.search() completes."""
    run_id: str
    params: SearchParams
    total_listings: int
    per_source: dict[str, int]
    errors: dict[str, str]       # source -> error message, empty if all OK
```

**Key design decisions for the model:**

- **Enums for controlled vocabularies** — `Source`, `SellerType`, `Drivetrain`, `Condition`, `FuelType` prevent garbage values and make queries predictable. Each normalizer maps API-specific strings (e.g., `"All Wheel Drive"` → `Drivetrain.AWD`).
- **EV-specific fields** — `battery_capacity_kwh`, `range_miles`, `fuel_type` are first-class. These are critical features for the ML model.
- **`raw` field** — always preserved. If a source returns fields we don't normalize yet, they're still in MongoDB for later extraction without re-fetching.
- **`to_mongo()` / `from_mongo()`** — handles the serialization boundary (Pydantic ↔ MongoDB). Enums are stored as strings. Datetimes stay as native BSON dates.
- **Validation at write time** — constructing a `Listing(...)` validates types and enum membership. Bad data from an API fails loud at normalization, not silently in Mongo.

### MongoDB indexes

Created by `ListingStore` on first connection:
- **`listings`**: unique compound index on `(source, source_id)` for dedup
- **`listings`**: index on `(make, model, year)` for search queries
- **`listings`**: index on `search_run_id` for grouping results by run
- **`search_runs`**: indexed by `started_at` descending

### Data access layer

**`src/store.py`** — Full CRUD data access layer using `pymongo`. Operates on `Listing` and `SearchRun` model instances (not raw dicts). This is the only module that talks to MongoDB — everything else goes through it.

```python
class ListingStore:
    def __init__(self, mongodb_uri: str = None, db_name: str = None):
        """Connect to MongoDB (defaults from config). Creates indexes on first init."""

    # ── Create ──
    def insert(self, listing: Listing) -> str:
        """Insert a new listing. Returns the MongoDB _id. Raises on duplicate (source, source_id)."""

    def insert_many(self, listings: list[Listing]) -> int:
        """Insert multiple listings. Skips duplicates. Returns count inserted."""

    # ── Read ──
    def get_by_id(self, id: str) -> Listing | None:
        """Fetch a single listing by MongoDB _id."""

    def get_by_source(self, source: str, source_id: str) -> Listing | None:
        """Fetch a single listing by its source + source_id compound key."""

    def find(self, query: dict, sort: list[tuple] | None = None,
             limit: int = 0, skip: int = 0) -> list[Listing]:
        """Query listings. Returns Listing model instances."""

    def find_by_vehicle(self, make: str, model: str,
                        year_min: int | None = None,
                        year_max: int | None = None) -> list[Listing]:
        """Convenience: find all listings for a make/model/year range."""

    def find_by_run(self, run_id: str) -> list[Listing]:
        """All listings from a specific search run."""

    def count(self, query: dict = None) -> int:
        """Count matching listings."""

    # ── Update ──
    def update(self, id: str, updates: dict) -> bool:
        """Partial update by _id. `updates` is a dict of field->value. Returns True if modified."""

    def upsert(self, listing: Listing) -> bool:
        """Insert or update by (source, source_id). Returns True if new, False if updated."""

    def upsert_many(self, listings: list[Listing]) -> dict:
        """Bulk upsert. Returns {"inserted": N, "updated": N}."""

    # ── Delete ──
    def delete(self, id: str) -> bool:
        """Delete a single listing by _id. Returns True if deleted."""

    def delete_by_run(self, run_id: str) -> int:
        """Delete all listings from a search run. Returns count deleted."""

    def delete_by_query(self, query: dict) -> int:
        """Delete all listings matching a query. Returns count deleted."""

    # ── Search runs ──
    def save_search_run(self, run: SearchRun) -> str:
        """Save search run metadata. Returns run.id."""

    def get_search_run(self, run_id: str) -> SearchRun | None:
        """Retrieve a search run by ID."""

    def list_search_runs(self, limit: int = 20) -> list[SearchRun]:
        """List recent search runs, newest first."""
```

**Design notes:**
- `upsert` / `upsert_many` are what `VehicleSearch` uses during search-and-store. The compound key `(source, source_id)` prevents duplicates across runs.
- `find`, `find_by_vehicle`, `find_by_run` are the read methods the ML pipeline will use to pull training data.
- `update` takes a partial dict (not a full `Listing`) so callers can patch individual fields (e.g., mark a listing as stale).
- `delete_by_run` is useful for clearing bad data from a failed search.
- All read methods return `Listing` model instances via `Listing.from_mongo()`.

### Aggregation layer

**`src/vehicle_search.py`** — `VehicleSearch` class. This is the main user-facing abstraction. Delegates all persistence to `ListingStore`.

```python
class VehicleSearch:
    def __init__(self, store: ListingStore = None):
        """Initializes all four clients from config and the ListingStore DAL."""

    def search(
        self,
        make: str,
        model: str,
        year_min: int | None = None,
        year_max: int | None = None,
        zip: str | None = None,
        radius: int | None = None,
        sources: list[str] | None = None,  # filter to specific sources, default=all
        max_pages: int = 10,
    ) -> SearchResult:
        """
        Fan out to all (or selected) sources, normalize results,
        store in MongoDB, return summary.
        """

    def _fetch_marketcheck(self, params) -> list[dict]: ...
    def _fetch_autodev(self, params) -> list[dict]: ...
    def _fetch_drivly(self, params) -> list[dict]: ...
    def _fetch_carapis(self, params) -> list[dict]: ...

    def _normalize(self, source: str, raw: dict, run_id: str) -> Listing:
        """
        Maps a raw API response dict to a validated Listing model.
        Each source has its own field mapping. Enum values are
        coerced (e.g. "All Wheel Drive" → Drivetrain.AWD).
        """
```

**Behavior:**
1. Creates a `search_run` record in MongoDB with the params and `started_at` timestamp
2. Iterates over each source (or the subset specified in `sources`)
3. Calls the corresponding `_fetch_*` method, which delegates to the bespoke client
4. Each raw result is passed through `_normalize()` to produce a validated `Listing` model instance
5. Validated `Listing` objects are bulk-upserted to MongoDB via `store.upsert_many()`
6. If a source errors, catches the exception, records `"status": "error"` in the search run, and continues to the next source — one failure doesn't block the others
7. Updates the `search_run` record with `completed_at` and per-source counts
8. Returns a `SearchResult` dataclass:

```python
@dataclass
class SearchResult:
    run_id: str
    params: dict
    total_listings: int
    per_source: dict[str, int]
    errors: dict[str, str]   # source -> error message, empty if all succeeded
```

**Normalization mappings** are fully documented in [api-response-mappings.md](api-response-mappings.md) with:
- Complete response objects from each API (actual JSON from their docs)
- Field-by-field mapping tables from each source to the `Listing` model
- Transform rules for enums (drivetrain, fuel_type, condition, seller_type)
- A field coverage matrix showing which fields are available from which sources

The implementing agent **must read that file** when writing `_normalize()`. Example for MarketCheck:

```python
{
    "source": "marketcheck",
    "source_id": raw["id"],
    "make": raw["build"]["make"],
    "model": raw["build"]["model"],
    "year": raw["build"]["year"],
    "trim": raw["build"].get("trim"),
    "mileage": raw.get("miles"),
    "price": raw.get("price"),
    "drivetrain": raw["build"].get("drivetrain"),
    "exterior_color": raw.get("exterior_color"),
    ...
    "raw": raw,
}
```

**`src/main.py`** — CLI entry point that:
1. Loads config
2. For each client: calls a basic search (e.g., 2023 Tesla Model 3, first page only), prints the count and first result
3. Runs a `VehicleSearch.search()` aggregated search, prints the `SearchResult` summary
4. Reports which clients succeeded / failed
5. Usage: `uv run python src/main.py`

## Technical implementation detail

### 1. Layout

See directory layout above. All source code under `src/`. No nested packages beyond `src/clients/`.

### 2. Data and APIs

Each client returns the raw JSON shape from its respective API. The `VehicleSearch` layer normalizes these to a common MongoDB document schema (see Storage layer above). Source API docs:
- MarketCheck: https://docs.marketcheck.com/docs/api/cars
- Auto.dev: https://docs.auto.dev/v2/products/vehicle-listings
- Driv.ly: https://docs.driv.ly
- Carapis: https://docs.carapis.com/parsers/cargurus.com/api-reference

### 3. Data flow

**Individual client call:**
```
client.search_active(make="Tesla", model="Model 3", year=2023)
  → Client builds query params
  → GET to API with auth
  → Auto-paginate through all pages
  → Returns list[dict] (raw API shape)
```

**Aggregated search (primary usage):**
```
VehicleSearch.search(make="Tesla", model="Model 3", year_min=2022, year_max=2024)
  → Creates search_run record in MongoDB
  → For each source:
      → Calls _fetch_*(params) → delegates to bespoke client
      → Passes each raw result through _normalize(source, raw)
      → Bulk upserts normalized listings to MongoDB (dedup on source + source_id)
      → Records count and status in search_run
      → If source errors: logs error, continues to next source
  → Updates search_run with completed_at and totals
  → Returns SearchResult dataclass
```

### 4. Integrations

- **4 external APIs** — HTTP services authenticated via API keys stored in `.env`
- **MongoDB** — runs via `docker-compose.yml` on `localhost:27017`. Connection string in `.env` (`MONGODB_URI`). Two collections: `listings` (compound unique index on `source` + `source_id`) and `search_runs`. Data persisted to a named Docker volume.

### 5. Frontend integration

N/A — this is a backend/utility module only.

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| API docs are stale or endpoints have changed since research | Medium | Each client's smoke test in `main.py` validates connectivity immediately. Fix on contact. |
| Free tier rate limits hit during development | Medium | Keep test queries small (single make/model/year, limit rows). `max_pages` safety param on every client and on `VehicleSearch.search()`. |
| Driv.ly or Carapis API structure differs significantly from what docs suggest | Medium | These are the least-documented APIs. Build them last. Accept they may need iteration. Normalization mapping may need adjustment once real responses are seen. |
| OAuth 2.0 flow for MarketCheck is more complex than simple key auth | Low | Start with API key auth (query param). Only implement OAuth if key auth is rejected. |
| Normalization loses important source-specific fields | Low | `raw` dict is always preserved in MongoDB. Can extract additional fields later without re-fetching. |
| MongoDB not running locally | Low | `docker compose up -d` is all that's needed. `SETUP.md` covers this. |

## Open decisions

All decisions resolved during design:
- Bespoke clients (not common interface) — normalization happens in the `VehicleSearch` aggregation layer
- Auto-pagination with `max_pages` safety valve
- `uv` as package manager
- MongoDB for storage with compound dedup key `(source, source_id)`
- Raw API responses preserved alongside normalized fields

## Deliverables Manifest

1. NEW  `pyproject.toml` — Project config with dependencies: `requests`, `python-dotenv`, `pymongo`, `pydantic`; requires Python >=3.11
2. NEW  `docker-compose.yml` — MongoDB 7 container with named volume for data persistence, exposes `27017`
3. NEW  `.env.example` — Template with all required API key variables, `MONGODB_URI`, `MONGODB_DB_NAME`, and inline comments
4. MOD  `.gitignore` — Add `.env`, `__pycache__`, `.venv`
5. NEW  `SETUP.md` — Step-by-step account creation and API key setup guide with portal links for all four services, plus `docker compose up -d` for MongoDB
6. NEW  `src/__init__.py` — Empty package init
7. NEW  `src/config.py` — Loads `.env`, exposes API keys and MongoDB config, raises on missing keys
8. NEW  `src/models.py` — Pydantic data models: `Listing`, `SearchRun`, `SearchResult`, `SearchParams`, enums (`Source`, `SellerType`, `Drivetrain`, `Condition`, `FuelType`), with `to_mongo()`/`from_mongo()` serialization
9. NEW  `src/clients/__init__.py` — Exports all four client classes
10. NEW `src/clients/marketcheck.py` — `MarketCheckClient` with search, listing, VIN endpoints + auto-pagination
11. NEW `src/clients/autodev.py` — `AutoDevClient` with search, VIN decode endpoints + auto-pagination
12. NEW `src/clients/drivly.py` — `DrivlyClient` with listings, VIN, prices endpoints + auto-pagination
13. NEW `src/clients/carapis.py` — `CarapisClient` with search, listing endpoints + auto-pagination
14. NEW `src/store.py` — `ListingStore` CRUD data access layer: full create/read/update/delete on `Listing` and `SearchRun` models, dedup via compound index, convenience queries (`find_by_vehicle`, `find_by_run`), bulk upsert, index creation
15. NEW `src/vehicle_search.py` — `VehicleSearch` class: fans out to all clients, normalizes raw responses to `Listing` models, stores in MongoDB, returns `SearchResult`. Per-source error isolation.
16. NEW `src/main.py` — CLI entry point: smoke-tests individual clients, runs aggregated `VehicleSearch.search()`, prints summary

**Implementation protocol:** The implementing agent must follow the `plan-implementation` cursor rule when executing this plan.
