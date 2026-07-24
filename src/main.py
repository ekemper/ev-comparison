"""CLI entry point: smoke-test individual clients and run an aggregated search."""

from __future__ import annotations

import argparse
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

MAKE = "Tesla"
MODEL = "Model 3"
YEAR_MIN = 2022
YEAR_MAX = 2024


def _preview(listings: list[dict], n: int = 2) -> None:
    for item in listings[:n]:
        print(json.dumps(item, indent=2, default=str)[:1200])
        if len(json.dumps(item, default=str)) > 1200:
            print("  ... (truncated)")


def _available_sources() -> list[str]:
    from src import config

    sources = []
    if config.MARKETCHECK_API_KEY:
        sources.append("marketcheck")
    if config.AUTODEV_API_KEY:
        sources.append("autodev")
    if config.DRIVLY_API_KEY:
        sources.append("drivly")
    if config.CARAPIS_API_KEY:
        sources.append("carapis")
    return sources


def smoke_test_clients(sources: list[str]) -> None:
    """Hit each configured API with a minimal first-page request."""
    from src.clients import AutoDevClient, CarapisClient, DrivlyClient, MarketCheckClient

    registry: dict[str, tuple[type, str]] = {
        "marketcheck": (MarketCheckClient, "search_active"),
        "autodev": (AutoDevClient, "search_listings"),
        "drivly": (DrivlyClient, "get_listings"),
        "carapis": (CarapisClient, "search"),
    }

    for name in sources:
        if name not in registry:
            continue
        cls, method = registry[name]
        print(f"\n{'='*60}")
        print(f"  {name} — smoke test (first page only)")
        print(f"{'='*60}")
        try:
            client = cls()
            fn = getattr(client, method)
            results = fn(make=MAKE, model=MODEL, year_min=YEAR_MIN, year_max=YEAR_MAX, max_pages=1)
            print(f"  Returned {len(results)} listings")
            if results:
                _preview(results)
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")


def aggregated_search(sources: list[str]) -> None:
    """Run VehicleSearch across configured sources and print summary."""
    from src.store import ListingStore
    from src.vehicle_search import VehicleSearch

    print(f"\n{'='*60}")
    print("  Aggregated VehicleSearch")
    print(f"{'='*60}")

    store = ListingStore()
    vs = VehicleSearch(store=store)
    result = vs.search(
        make=MAKE,
        model=MODEL,
        year_min=YEAR_MIN,
        year_max=YEAR_MAX,
        sources=sources,
        max_pages=2,
    )

    print(f"\n  Run ID:  {result.run_id}")
    print(f"  Total:   {result.total_listings} listings")
    print(f"  Params:  {result.params.make} {result.params.model} "
          f"({result.params.year_min}-{result.params.year_max})")
    print()
    for source, count in result.per_source.items():
        status = "OK" if source not in result.errors else "FAIL"
        print(f"  {source:15s}  {count:>5d} listings  [{status}]")
    if result.errors:
        print()
        for source, err in result.errors.items():
            print(f"  {source} error: {err}")

    total_in_db = store.count()
    print(f"\n  Total listings in MongoDB: {total_in_db}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EV Comparison — API smoke test")
    parser.add_argument(
        "--source", "-s",
        choices=["marketcheck", "autodev", "drivly", "carapis"],
        help="Test a specific source only (default: all configured)",
    )
    parser.add_argument(
        "--skip-db", action="store_true",
        help="Only run smoke tests, skip aggregated search (no MongoDB needed)",
    )
    args = parser.parse_args()

    available = _available_sources()
    if not available:
        print("ERROR: No API keys configured in .env — see SETUP.md")
        raise SystemExit(1)

    sources = [args.source] if args.source else available
    missing = [s for s in sources if s not in available]
    if missing:
        print(f"ERROR: No API key for: {', '.join(missing)}")
        raise SystemExit(1)

    print(f"EV Comparison — API Client Smoke Test")
    print(f"Search: {MAKE} {MODEL} ({YEAR_MIN}–{YEAR_MAX})")
    print(f"Sources: {', '.join(sources)}")

    smoke_test_clients(sources)

    if not args.skip_db:
        aggregated_search(sources)
    else:
        print("\n  (--skip-db: skipping aggregated search)")

    print(f"\n{'='*60}")
    print("  Done.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
