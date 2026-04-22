"""Persist test/scenario outcomes in their own ChromaDB collection.

Each outcome is embedded and stored so the RAG retriever can surface relevant
prior results alongside textbook passages when answering future queries.
"""
import hashlib
import logging
from datetime import datetime, timezone

import chromadb
import chromadb.api

from rag.ingest import get_embedder, _get_client

logger = logging.getLogger(__name__)

OUTCOMES_COLLECTION = "outcomes"

_outcomes_col: chromadb.Collection | None = None  # type: ignore[type-arg]


def get_outcomes_collection() -> chromadb.Collection:
    global _outcomes_col
    if _outcomes_col is None:
        _outcomes_col = _get_client().get_or_create_collection(
            OUTCOMES_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _outcomes_col


def record_outcome(
    scenario: str,
    result: str,
    learned: str,
    category: str = "general",
    success: bool = True,
) -> str:
    """Store a test/scenario outcome. Returns the generated outcome ID."""
    embedder = get_embedder()
    col = get_outcomes_collection()

    # Combine all fields into a single searchable document
    document = (
        f"SCENARIO: {scenario}\n"
        f"RESULT: {'SUCCESS' if success else 'FAILURE'}\n"
        f"OUTCOME: {result}\n"
        f"LESSON: {learned}"
    )

    oid = hashlib.md5(f"{scenario}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
    emb = next(embedder.embed([document])).tolist()

    col.upsert(
        ids=[oid],
        embeddings=[emb],
        documents=[document],
        metadatas=[{
            "category": category,
            "success": str(success),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }],
    )
    logger.info("Recorded outcome %s (category=%s)", oid, category)
    return oid


def list_outcomes(limit: int = 50) -> list[dict]:
    col = get_outcomes_collection()
    count = col.count()
    if count == 0:
        return []
    raw = col.get(
        limit=min(limit, count),
        include=["documents", "metadatas"],
    )
    outcomes = []
    for doc, meta, oid in zip(raw["documents"], raw["metadatas"], raw["ids"]):
        outcomes.append({"id": oid, "document": doc, **meta})
    return outcomes
