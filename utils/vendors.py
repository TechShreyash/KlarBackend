import asyncio
import logging
from typing import List, Tuple
from utils.db import db

logger = logging.getLogger(__name__)
vendordb = db.vendordb

VENDOR_DB: List[Tuple[str, str]] = [
    ("SuperStore Inc", "VEND_0001"),
    ("EZStore", "VEND_0002"),
]
# A lock MUST be used for all read/write operations to VENDOR_DB
VENDOR_DB_LOCK = asyncio.Lock()


async def get_current_vendors() -> List[Tuple[str, str]]:
    """Async-safe way to get a snapshot of the current vendor list."""
    async with VENDOR_DB_LOCK:
        # Return a copy to ensure thread-safety
        return list(VENDOR_DB)


async def get_or_create_vendor_id(extracted_name: str) -> str:
    """
    Async-safe function to find a vendor ID or create a new one.
    This is the *only* place new vendor IDs should be generated.
    """
    # Use a simple case-insensitive match.
    # For a real system, you'd use fuzzywuzzy or another fuzzy matching lib
    search_name = extracted_name.lower()

    async with VENDOR_DB_LOCK:
        # 1. Try to find an existing match
        for name, v_id in VENDOR_DB:
            if name.lower() == search_name:
                logger.info(
                    f"Matched '{extracted_name}' to existing vendor '{name}' ({v_id})"
                )
                return v_id

        # 2. No match found. Create a new one.
        logger.info(f"No match for '{extracted_name}'. Creating new vendor...")

        # Find the highest current ID
        numeric_ids = []
        for _, v_id in VENDOR_DB:
            try:
                numeric_ids.append(int(v_id.split("_")[-1]))
            except (ValueError, IndexError):
                continue  # Skip malformed IDs

        new_id_num = max(numeric_ids) + 1 if numeric_ids else 1
        new_vendor_id = f"VEND_{new_id_num:04d}"

        # 3. Add to DB and return
        VENDOR_DB.append((extracted_name, new_vendor_id))
        logger.info(f"Created new vendor: {extracted_name} ({new_vendor_id})")

        return new_vendor_id
