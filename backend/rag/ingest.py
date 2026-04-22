"""Parse PDFs from book_data/, chunk them, embed, and upsert into ChromaDB."""
import hashlib
import logging
from pathlib import Path

import fitz  # PyMuPDF
import chromadb
import chromadb.api
from sentence_transformers import SentenceTransformer

from config import settings
from rag.chunker import split_text

logger = logging.getLogger(__name__)

COLLECTION_NAME = "textbooks"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

_client: chromadb.api.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_embedder: SentenceTransformer | None = None


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


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logger.info("Loading embedding model %s …", EMBED_MODEL)
        _embedder = SentenceTransformer(EMBED_MODEL)
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

    ids, embeddings, documents, metadatas = [], [], [], []
    batch_size = 64

    def flush() -> None:
        if not ids:
            return
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        ids.clear(); embeddings.clear(); documents.clear(); metadatas.clear()

    new_chunks = 0
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if not text.strip():
            continue

        chunks = split_text(text, settings.chunk_size, settings.chunk_overlap)
        for idx, chunk in enumerate(chunks):
            cid = _chunk_id(full_name, page_num, idx)
            existing = collection.get(ids=[cid])
            if existing["ids"]:
                continue  # already ingested

            emb = embedder.encode(chunk.text, normalize_embeddings=True).tolist()
            ids.append(cid)
            embeddings.append(emb)
            documents.append(chunk.text)
            metadatas.append({
                "book": short_title,
                "page": page_num,
                "source": full_name,
            })
            new_chunks += 1

            if len(ids) >= batch_size:
                flush()

    flush()
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
