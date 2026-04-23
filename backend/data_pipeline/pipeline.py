"""Orchestrates the full PDF → QA pairs → JSONL dataset pipeline."""
import json
import logging
import random
import time
from pathlib import Path

import fitz  # PyMuPDF
import anthropic
from tqdm import tqdm

from data_pipeline.cleaner import clean_page_text, is_mostly_code
from data_pipeline.splitter import split_into_chunks
from data_pipeline.qa_generator import generate_qa_pairs, QAPair

logger = logging.getLogger(__name__)

# System prompt baked into every training example so the fine-tuned model
# inherits SecurityAI's identity and tone.
_FINETUNE_SYSTEM = (
    "You are SecurityAI, an expert cybersecurity assistant specializing in "
    "secure application development, penetration testing, and reverse engineering. "
    "You provide accurate, practical guidance grounded in authoritative security literature."
)

_BOOK_TITLES: dict[str, str] = {
    "Gray Hat": "Gray Hat Hacking",
    "Reversing": "Reversing: Secrets of Reverse Engineering",
    "reverse": "Reversing: Secrets of Reverse Engineering",
}


def _book_title(path: Path) -> str:
    for key, title in _BOOK_TITLES.items():
        if key in path.stem:
            return title
    return path.stem[:60]


def _extract_chunks(pdf_path: Path, target_words: int) -> list[tuple[str, str]]:
    """Return (chunk_text, book_title) pairs from a single PDF."""
    title = _book_title(pdf_path)
    doc = fitz.open(str(pdf_path))
    results: list[tuple[str, str]] = []

    for page in doc:
        raw = page.get_text()
        cleaned = clean_page_text(raw)
        if not cleaned or is_mostly_code(cleaned):
            continue
        for chunk in split_into_chunks(cleaned, target_words=target_words):
            results.append((chunk, title))

    doc.close()
    return results


def _to_chatml(pair: QAPair) -> dict:
    """Convert a QAPair to the ChatML format expected by fine-tuning frameworks."""
    return {
        "messages": [
            {"role": "system",    "content": _FINETUNE_SYSTEM},
            {"role": "user",      "content": pair.question},
            {"role": "assistant", "content": pair.answer},
        ]
    }


def _write_jsonl(pairs: list[QAPair], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(_to_chatml(pair), ensure_ascii=False) + "\n")


def run_pipeline(
    books_dir: Path,
    output_dir: Path,
    api_key: str,
    n_pairs: int = 3,
    test_ratio: float = 0.15,
    target_words: int = 200,
    request_delay: float = 0.3,
    seed: int = 42,
) -> dict:
    """Run the full data generation pipeline end-to-end.

    Args:
        books_dir:      Directory containing PDF textbooks.
        output_dir:     Where to write train.jsonl, test.jsonl, stats.json.
        api_key:        Anthropic API key.
        n_pairs:        QA pairs to generate per chunk.
        test_ratio:     Fraction of pairs held out for the test set.
        target_words:   Target chunk size in words.
        request_delay:  Seconds to sleep between API calls (rate-limit buffer).
        seed:           Random seed for reproducible train/test split.

    Returns:
        dict with dataset statistics.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(seed)

    client = anthropic.Anthropic(api_key=api_key)

    # ── 1. Extract chunks from all PDFs ───────────────────────────────────────
    pdf_paths = sorted(books_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found in {books_dir}")

    all_chunks: list[tuple[str, str]] = []
    for path in pdf_paths:
        chunks = _extract_chunks(path, target_words)
        logger.info("%s → %d chunks", path.name, len(chunks))
        all_chunks.extend(chunks)

    logger.info("Total chunks to process: %d", len(all_chunks))
    logger.info("Estimated API calls: %d  |  pairs target: ~%d",
                len(all_chunks), len(all_chunks) * n_pairs)

    # ── 2. Generate QA pairs (streaming to disk as we go) ────────────────────
    all_pairs: list[QAPair] = []
    raw_path = output_dir / "raw_qa_pairs.jsonl"
    skipped = 0

    with open(raw_path, "w", encoding="utf-8") as raw_file:
        for chunk_text, book_title in tqdm(all_chunks, desc="Generating QA pairs", unit="chunk"):
            pairs = generate_qa_pairs(client, chunk_text, book_title, n_pairs)

            if not pairs:
                skipped += 1
            else:
                for pair in pairs:
                    all_pairs.append(pair)
                    raw_file.write(json.dumps({
                        "question":      pair.question,
                        "answer":        pair.answer,
                        "question_type": pair.question_type,
                        "book":          pair.book,
                    }, ensure_ascii=False) + "\n")
                raw_file.flush()

            if request_delay > 0:
                time.sleep(request_delay)

    logger.info("Generation complete: %d pairs from %d chunks (%d skipped)",
                len(all_pairs), len(all_chunks), skipped)

    # ── 3. Shuffle and split ──────────────────────────────────────────────────
    random.shuffle(all_pairs)
    n_test = max(1, int(len(all_pairs) * test_ratio))
    test_pairs  = all_pairs[:n_test]
    train_pairs = all_pairs[n_test:]

    # ── 4. Write ChatML JSONL files ───────────────────────────────────────────
    _write_jsonl(train_pairs, output_dir / "train.jsonl")
    _write_jsonl(test_pairs,  output_dir / "test.jsonl")

    # ── 5. Write stats ────────────────────────────────────────────────────────
    type_counts: dict[str, int] = {}
    book_counts:  dict[str, int] = {}
    for pair in all_pairs:
        type_counts[pair.question_type] = type_counts.get(pair.question_type, 0) + 1
        book_counts[pair.book]           = book_counts.get(pair.book, 0) + 1

    stats = {
        "total_pairs":      len(all_pairs),
        "train_pairs":      len(train_pairs),
        "test_pairs":       len(test_pairs),
        "chunks_processed": len(all_chunks),
        "chunks_skipped":   skipped,
        "pdfs_processed":   len(pdf_paths),
        "question_types":   type_counts,
        "pairs_per_book":   book_counts,
    }
    with open(output_dir / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    return stats
