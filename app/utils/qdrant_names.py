"""
Qdrant Collection Naming Helpers
================================

Root cause of many Qdrant runtime failures:
- Collection created with one vector dimension (e.g., 1536)
- Code later switches embedding model (e.g., 3072)
- Qdrant rejects queries/upserts with: "Vector dimension error"

Solution:
- Use dimension-suffixed collections by default (e.g., `character_memories_d3072`)
  so different embedding models don't collide.
"""

from __future__ import annotations

import os

def _suffix_enabled() -> bool:
    return os.getenv("QDRANT_SUFFIX_BY_DIM", "true").lower() in ("1", "true", "yes", "y", "on")


def qdrant_collection_name_for_dim(base: str, dim: int) -> str:
    """Return `{base}_d{dim}` if suffixing is enabled, else `base`."""
    if not _suffix_enabled():
        return base
    return f"{base}_d{int(dim)}"


def qdrant_collection_name_for_vector(base: str, vector: object) -> str:
    """Derive dim from a vector-like object (len(vector)) and return the effective collection name."""
    try:
        dim = len(vector)  # type: ignore[arg-type]
    except Exception:
        # Fallback to base if we can't infer dim.
        return base
    return qdrant_collection_name_for_dim(base, dim)


def qdrant_collection_name(base: str) -> str:
    """
    Backwards-compatible helper:
    If suffixing is enabled but we don't know the dim, just return `base`.
    Prefer `qdrant_collection_name_for_dim(...)` / `..._for_vector(...)` in new code.
    """
    return base


