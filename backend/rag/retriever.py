"""Query textbook and outcomes collections, returning merged ranked context."""
from dataclasses import dataclass

from config import settings
from rag.ingest import get_collection, get_embedder
from learning.store import get_outcomes_collection


@dataclass
class RetrievedChunk:
    text: str
    book: str
    page: int | None
    score: float
    source_type: str  # "textbook" | "outcome"


def retrieve(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    k = top_k or settings.top_k_results
    embedder = get_embedder()
    query_emb = embedder.encode(query, normalize_embeddings=True).tolist()

    results: list[RetrievedChunk] = []

    # --- textbook collection ---
    try:
        col = get_collection()
        if col.count() > 0:
            raw = col.query(
                query_embeddings=[query_emb],
                n_results=min(k, col.count()),
                include=["documents", "metadatas", "distances"],
            )
            for doc, meta, dist in zip(
                raw["documents"][0],
                raw["metadatas"][0],
                raw["distances"][0],
            ):
                results.append(RetrievedChunk(
                    text=doc,
                    book=meta.get("book", "Unknown"),
                    page=meta.get("page"),
                    score=1.0 - float(dist),  # cosine distance → similarity
                    source_type="textbook",
                ))
    except Exception:
        pass

    # --- learned outcomes collection ---
    try:
        outcomes_col = get_outcomes_collection()
        if outcomes_col.count() > 0:
            raw = outcomes_col.query(
                query_embeddings=[query_emb],
                n_results=min(max(k // 2, 2), outcomes_col.count()),
                include=["documents", "metadatas", "distances"],
            )
            for doc, meta, dist in zip(
                raw["documents"][0],
                raw["metadatas"][0],
                raw["distances"][0],
            ):
                results.append(RetrievedChunk(
                    text=doc,
                    book=f"Learned: {meta.get('category', 'general')}",
                    page=None,
                    score=1.0 - float(dist),
                    source_type="outcome",
                ))
    except Exception:
        pass

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:k]


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a context block for the LLM prompt."""
    if not chunks:
        return ""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.book
        if chunk.page:
            source += f", p.{chunk.page}"
        parts.append(f"[{i}] ({source})\n{chunk.text}")
    return "\n\n".join(parts)
