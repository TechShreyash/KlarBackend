import asyncio
import logging
from typing import List, Tuple, Optional

from datetime import datetime
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from utils.db import db

logger = logging.getLogger(__name__)
vendordb = db.vendordb  # MongoDB collection (async/motor)

# -----------------------------
# In-memory vendor cache
# -----------------------------
VENDOR_DB: List[Tuple[str, str]] = [
    ("SuperStore Inc", "VEND_0001"),
    ("EZStore", "VEND_0002"),
]
# A lock MUST be used for all read/write operations to VENDOR_DB
VENDOR_DB_LOCK = asyncio.Lock()


# -----------------------------
# Helpers
# -----------------------------
def _normalize_name(name: str) -> str:
    """Return a lowercased, trimmed version of the name for case-insensitive equality."""
    return (name or "").strip().lower()


async def _ensure_indexes() -> None:
    """
    Ensure indexes exist for fast lookup and uniqueness.
    - vendor_id unique
    - normalized_name unique (case-insensitive equivalence)
    """
    try:
        await vendordb.create_index(
            [("vendor_id", ASCENDING)], unique=True, name="ux_vendor_id"
        )
        await vendordb.create_index(
            [("normalized_name", ASCENDING)],
            unique=True,
            name="ux_normalized_name",
        )
    except Exception as e:
        logger.exception("Failed creating indexes on vendordb: %s", e)


def _extract_numeric(vendor_id: str) -> Optional[int]:
    """Extract numeric suffix from IDs like VEND_0001 -> 1. Return None on failure."""
    try:
        return int(vendor_id.split("_")[-1])
    except Exception:
        return None


async def _generate_next_vendor_id() -> str:
    """
    Generate the next vendor ID by looking at both MongoDB and the in-memory cache.
    Pattern: VEND_XXXX with zero-padded 4 digits.
    """
    # Highest in memory
    async with VENDOR_DB_LOCK:
        mem_max = (
            max((_extract_numeric(v_id) or 0) for _, v_id in VENDOR_DB)
            if VENDOR_DB
            else 0
        )

    # Highest in Mongo
    mongo_max = 0
    doc = await vendordb.find_one(
        {},
        projection={"vendor_id": 1, "_id": 0},
        sort=[("vendor_id", DESCENDING)],
    )
    if doc and isinstance(doc.get("vendor_id"), str):
        mongo_max = _extract_numeric(doc["vendor_id"]) or 0

    next_num = max(mem_max, mongo_max) + 1
    return f"VEND_{next_num:04d}"


# -----------------------------
# Public API
# -----------------------------
async def init_vendor_db_cache_on_startup() -> None:
    """
    Call this once on application startup.
    - Ensures indexes
    - Loads all vendors from MongoDB into the in-memory VENDOR_DB cache
    - Merges with any hardcoded seed entries without duplicating (case-insensitive)
    """
    await _ensure_indexes()

    # Load all vendors from Mongo
    vendors_from_mongo: List[Tuple[str, str]] = []
    try:
        cursor = vendordb.find(
            {},
            projection={"_id": 0, "name": 1, "vendor_id": 1, "normalized_name": 1},
            sort=[("vendor_id", ASCENDING)],
        )
        async for doc in cursor:
            name = doc.get("name")
            vendor_id = doc.get("vendor_id")
            if isinstance(name, str) and isinstance(vendor_id, str):
                vendors_from_mongo.append((name, vendor_id))
    except Exception as e:
        logger.exception("Error fetching vendors from MongoDB: %s", e)

    # Merge Mongo vendors with existing in-memory seed without duplicating by normalized name
    async with VENDOR_DB_LOCK:
        # Build a set of normalized names already present in memory
        existing_norms = {_normalize_name(n) for n, _ in VENDOR_DB}

        # Add Mongo ones that are not present yet
        for name, vid in vendors_from_mongo:
            if _normalize_name(name) not in existing_norms:
                VENDOR_DB.append((name, vid))
                existing_norms.add(_normalize_name(name))

    logger.info(
        "Vendor cache initialized with %d entries.", len(await get_current_vendors())
    )


async def get_current_vendors() -> List[Tuple[str, str]]:
    """Async-safe way to get a snapshot of the current vendor list."""
    async with VENDOR_DB_LOCK:
        # Return a copy to ensure safety
        return list(VENDOR_DB)


async def get_or_create_vendor_id(extracted_name: str) -> str:
    """
    Async-safe function to find a vendor ID or create a new one.
    This is the *only* place new vendor IDs should be generated.

    Behavior:
    1) Check in-memory cache (exact case-insensitive).
    2) If not found, check Mongo by normalized_name.
       - If found, add to cache and return.
    3) If still not found, generate a new ID, insert into Mongo,
       add to cache, and return.
    """
    if not extracted_name or not extracted_name.strip():
        raise ValueError("Vendor name must be a non-empty string.")

    search_norm = _normalize_name(extracted_name)

    # 1) Check memory cache
    async with VENDOR_DB_LOCK:
        for name, v_id in VENDOR_DB:
            if _normalize_name(name) == search_norm:
                logger.info(
                    "Matched '%s' to existing vendor '%s' (%s) [cache]",
                    extracted_name,
                    name,
                    v_id,
                )
                return v_id

    # 2) Check Mongo (outside the VENDOR_DB lock)
    mongo_doc = await vendordb.find_one(
        {"normalized_name": search_norm},
        projection={"_id": 0, "name": 1, "vendor_id": 1},
    )
    if mongo_doc:
        name = mongo_doc["name"]
        v_id = mongo_doc["vendor_id"]
        # Ensure the cache also has it
        async with VENDOR_DB_LOCK:
            # Re-check to avoid duplicates if another coroutine added it
            for n, vid in VENDOR_DB:
                if _normalize_name(n) == search_norm:
                    return vid
            VENDOR_DB.append((name, v_id))
        logger.info(
            "Matched '%s' to existing vendor '%s' (%s) [mongo]",
            extracted_name,
            name,
            v_id,
        )
        return v_id

    # 3) Create a new vendor
    logger.info("No match for '%s'. Creating new vendor...", extracted_name)

    # Generate new ID (checks both memory and Mongo)
    new_vendor_id = await _generate_next_vendor_id()

    doc = {
        "name": extracted_name,
        "normalized_name": search_norm,
        "vendor_id": new_vendor_id,
        "created_at": datetime.utcnow(),
    }

    # Insert into Mongo with duplicate handling (in case of race)
    try:
        await vendordb.insert_one(doc)
    except DuplicateKeyError:
        # Either the normalized_name or vendor_id collided; fetch again by normalized_name
        existing = await vendordb.find_one(
            {"normalized_name": search_norm},
            projection={"_id": 0, "name": 1, "vendor_id": 1},
        )
        if existing:
            # Someone else created it concurrently
            new_vendor_id = existing["vendor_id"]
            extracted_name = existing["name"]
        else:
            # Rare case: vendor_id collided but not name; regenerate vendor_id and retry once
            logger.warning("Vendor ID collision detected, regenerating vendor_id once.")
            new_vendor_id = await _generate_next_vendor_id()
            doc["vendor_id"] = new_vendor_id
            await vendordb.insert_one(doc)

    # Update in-memory cache
    async with VENDOR_DB_LOCK:
        # Final guard: only add if not already present by normalized name
        for n, _vid in VENDOR_DB:
            if _normalize_name(n) == search_norm:
                # Another coroutine added it while we were inserting; just return that ID
                # (ensure we return the exact ID stored)
                for nn, vv in VENDOR_DB:
                    if _normalize_name(nn) == search_norm:
                        logger.info(
                            "Created new vendor concurrently detected; returning cache ID %s",
                            vv,
                        )
                        return vv
        VENDOR_DB.append((extracted_name, new_vendor_id))

    logger.info("Created new vendor: %s (%s)", extracted_name, new_vendor_id)
    return new_vendor_id
