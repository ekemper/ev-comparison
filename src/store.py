from __future__ import annotations

import logging
from typing import Any

from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

from src import config
from src.models import Listing, SearchRun

logger = logging.getLogger(__name__)


class ListingStore:
    """Full CRUD data access layer for listings and search runs in MongoDB."""

    def __init__(
        self,
        mongodb_uri: str | None = None,
        db_name: str | None = None,
    ):
        uri = mongodb_uri or config.MONGODB_URI
        name = db_name or config.MONGODB_DB_NAME
        self.client = MongoClient(uri)
        self.db = self.client[name]
        self.listings = self.db["listings"]
        self.search_runs = self.db["search_runs"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.listings.create_index(
            [("source", 1), ("source_id", 1)],
            unique=True,
            name="ux_source_source_id",
        )
        self.listings.create_index(
            [("make", 1), ("model", 1), ("year", 1)],
            name="ix_make_model_year",
        )
        self.listings.create_index("search_run_id", name="ix_search_run_id")
        self.search_runs.create_index(
            [("started_at", -1)],
            name="ix_started_at",
        )

    # ── Create ──

    def insert(self, listing: Listing) -> str:
        result = self.listings.insert_one(listing.to_mongo())
        return str(result.inserted_id)

    def insert_many(self, listings: list[Listing]) -> int:
        if not listings:
            return 0
        docs = [l.to_mongo() for l in listings]
        try:
            result = self.listings.insert_many(docs, ordered=False)
            return len(result.inserted_ids)
        except BulkWriteError as e:
            inserted = e.details.get("nInserted", 0)
            logger.warning(
                "insert_many: %d inserted, %d duplicates skipped",
                inserted,
                len(listings) - inserted,
            )
            return inserted

    # ── Read ──

    def get_by_id(self, id: str) -> Listing | None:
        from bson import ObjectId

        doc = self.listings.find_one({"_id": ObjectId(id)})
        return Listing.from_mongo(doc) if doc else None

    def get_by_source(self, source: str, source_id: str) -> Listing | None:
        doc = self.listings.find_one({"source": source, "source_id": source_id})
        return Listing.from_mongo(doc) if doc else None

    def find(
        self,
        query: dict[str, Any],
        sort: list[tuple] | None = None,
        limit: int = 0,
        skip: int = 0,
    ) -> list[Listing]:
        cursor = self.listings.find(query)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return [Listing.from_mongo(doc) for doc in cursor]

    def find_by_vehicle(
        self,
        make: str,
        model: str,
        year_min: int | None = None,
        year_max: int | None = None,
    ) -> list[Listing]:
        query: dict[str, Any] = {
            "make": {"$regex": f"^{make}$", "$options": "i"},
            "model": {"$regex": f"^{model}$", "$options": "i"},
        }
        if year_min is not None or year_max is not None:
            year_filter: dict[str, int] = {}
            if year_min is not None:
                year_filter["$gte"] = year_min
            if year_max is not None:
                year_filter["$lte"] = year_max
            query["year"] = year_filter
        return self.find(query)

    def find_by_run(self, run_id: str) -> list[Listing]:
        return self.find({"search_run_id": run_id})

    def count(self, query: dict[str, Any] | None = None) -> int:
        return self.listings.count_documents(query or {})

    # ── Update ──

    def update(self, id: str, updates: dict[str, Any]) -> bool:
        from bson import ObjectId

        result = self.listings.update_one(
            {"_id": ObjectId(id)},
            {"$set": updates},
        )
        return result.modified_count > 0

    def upsert(self, listing: Listing) -> bool:
        """Insert or update by (source, source_id). Returns True if new."""
        doc = listing.to_mongo()
        result = self.listings.update_one(
            {"source": listing.source.value, "source_id": listing.source_id},
            {"$set": doc},
            upsert=True,
        )
        return result.upserted_id is not None

    def upsert_many(self, listings: list[Listing]) -> dict[str, int]:
        """Bulk upsert. Returns {"inserted": N, "updated": N}."""
        if not listings:
            return {"inserted": 0, "updated": 0}

        ops = []
        for listing in listings:
            doc = listing.to_mongo()
            ops.append(
                UpdateOne(
                    {"source": listing.source.value, "source_id": listing.source_id},
                    {"$set": doc},
                    upsert=True,
                )
            )

        result = self.listings.bulk_write(ops, ordered=False)
        return {
            "inserted": result.upserted_count,
            "updated": result.modified_count,
        }

    # ── Delete ──

    def delete(self, id: str) -> bool:
        from bson import ObjectId

        result = self.listings.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    def delete_by_run(self, run_id: str) -> int:
        result = self.listings.delete_many({"search_run_id": run_id})
        return result.deleted_count

    def delete_by_query(self, query: dict[str, Any]) -> int:
        result = self.listings.delete_many(query)
        return result.deleted_count

    # ── Search runs ──

    def save_search_run(self, run: SearchRun) -> str:
        doc = run.to_mongo()
        self.search_runs.replace_one({"_id": doc["_id"]}, doc, upsert=True)
        return run.id

    def get_search_run(self, run_id: str) -> SearchRun | None:
        doc = self.search_runs.find_one({"_id": run_id})
        return SearchRun.from_mongo(doc) if doc else None

    def list_search_runs(self, limit: int = 20) -> list[SearchRun]:
        cursor = self.search_runs.find().sort("started_at", -1).limit(limit)
        return [SearchRun.from_mongo(doc) for doc in cursor]
