"""
Qdrant Client Compatibility Helpers
==================================

Why this exists:
- qdrant-client has evolved its public API over time (e.g., `search()` vs `query_points()`).
- This project uses Qdrant in multiple places (ingestion, v2 RAG, long-term memory).
- A small wrapper avoids repeating version-specific branching and makes upgrades safer.
"""

from __future__ import annotations

from typing import Any, List, Optional

from qdrant_client.models import Filter


def query_points_compat(
    client: Any,
    *,
    collection_name: str,
    query_vector: List[float],
    limit: int,
    query_filter: Optional[Filter] = None,
    with_payload: bool = True,
) -> List[Any]:
    """
    Return a list of scored points for a vector similarity query.

    Supports:
    - qdrant-client >= 1.16: `client.query_points(...)` returning QueryResponse(points=[...])
    - older/newer surfaces: `client.search(...)` returning list[ScoredPoint]
    - fallback: `client.query(...)` returning QueryResponse-like objects
    """
    # Preferred (qdrant-client 1.16+)
    if hasattr(client, "query_points"):
        res = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=with_payload,
            query_filter=query_filter,
        )
        return getattr(res, "points", []) or []

    # Older surface (some versions)
    if hasattr(client, "search"):
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
        ) or []

    # Last resort
    if hasattr(client, "query"):
        res = client.query(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=with_payload,
            query_filter=query_filter,
        )
        return getattr(res, "points", []) or []

    return []


