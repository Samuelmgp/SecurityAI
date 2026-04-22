"""Parse PDFs from book_data/, chunk them, embed, and upsert into ChromaDB."""
import hashlib
import logging
from pathlib import Path

import fitz  # PyMuPDF
import chromadb
import chromadb.api
from fastembed import TextEmbedding

from config import settings
from rag.chunker import split_text

logger = logging.getLogger(__name__)

COLLECTION_NAME = "textbooks"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

_client: chromadb.api.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_embedder: TextEmbedding | None = None


def _get_client() -> chromadb.api.ClientAPI:
    global _client
    if _client is None:
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(settings.chroma_path))
    return _client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        _collection = _get_client().get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        logger.info("Loading embedding model %s …", EMBED_MODEL)
        _embedder = TextEmbedding(EMBED_MODEL)
    return _embedder


def _chunk_id(pdf_name: str, page: int, chunk_idx: int) -> str:
    raw = f"{pdf_name}:p{page}:c{chunk_idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def _extract_book_meta(path: Path) -> tuple[str, str]:
    """Return (short_title, full_filename) from the PDF path."""
    name = path.stem
    if "Gray Hat" in name:
        short = "Gray Hat Hacking"
    elif "Reversing" in name or "reverse" in name.lower():
        short = "Reversing: RE Secrets"
    else:
        short = name[:40]
    return short, name


def ingest_pdf(path: Path) -> int:
    """Ingest a single PDF. Returns number of new chunks upserted."""
    collection = get_collection()
    embedder = get_embedder()
    short_title, full_name = _extract_book_meta(path)

    logger.info("Ingesting %s …", short_title)
    doc = fitz.open(str(path))

    # Collect all new chunks first, then batch-embed for efficiency
    pending_ids, pending_texts, pending_meta = [], [], []
    batch_size = 64

    def flush(texts: list[str]) -> None:
        if not texts:
            return
        vecs = list(embedder.embed(texts))
        collection.upsert(
            ids=pending_ids[:],
            embeddings=[v.tolist() for v in vecs],
            documents=texts,
            metadatas=pending_meta[:],
        )
        pending_ids.clear()
        pending_texts.clear()
        pending_meta.clear()

    new_chunks = 0
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if not text.strip():
            continue

        for idx, chunk in enumerate(split_text(text, settings.chunk_size, settings.chunk_overlap)):
            cid = _chunk_id(full_name, page_num, idx)
            if collection.get(ids=[cid])["ids"]:
                continue  # already ingested

            pending_ids.append(cid)
            pending_texts.append(chunk.text)
            pending_meta.append({"book": short_title, "page": page_num, "source": full_name})
            new_chunks += 1

            if len(pending_ids) >= batch_size:
                flush(pending_texts[:])

    flush(pending_texts[:])
    doc.close()
    logger.info("  → %d new chunks from %s", new_chunks, short_title)
    return new_chunks


def ingest_all() -> dict[str, int]:
    """Ingest all PDFs in book_data/. Idempotent — skips already-stored chunks."""
    results: dict[str, int] = {}
    pdf_paths = sorted(settings.books_path.glob("*.pdf"))
    if not pdf_paths:
        logger.warning("No PDFs found in %s", settings.books_path)
        return results

    for path in pdf_paths:
        try:
            count = ingest_pdf(path)
            results[path.name] = count
        except Exception:
            logger.exception("Failed to ingest %s", path.name)
            results[path.name] = -1

    return results
