"""
Embedding Dimension Helpers
==========================

Multiple parts of the codebase need to agree on the embedding vector size:
- Qdrant collection creation
- Qdrant queries (query vector length must match collection config)

This module centralizes the logic to determine the effective embedding dimension
from environment variables.
"""

from __future__ import annotations

import os


_MODEL_DIMS = {
    # OpenAI embeddings
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
    # Common local defaults (best-effort; override via VECTOR_SIZE if needed)
    "BAAI/bge-small-en-v1.5": 384,
}


def get_vector_size() -> int:
    """
    Determine the embedding vector size.

    Priority:
    1) Explicit VECTOR_SIZE env var (authoritative override)
    2) EMBEDDING_MODEL / LLM_EMBEDDING_MODEL env vars (common in this repo)
    3) Default 1536
    """
    explicit = os.getenv("VECTOR_SIZE")
    if explicit:
        try:
            return int(explicit)
        except ValueError:
            pass

    model = (
        os.getenv("EMBEDDING_MODEL")
        or os.getenv("LLM_EMBEDDING_MODEL")
        or os.getenv("OPENAI_EMBEDDING_MODEL")
    )
    if model:
        return int(_MODEL_DIMS.get(model, 1536))

    return 1536


