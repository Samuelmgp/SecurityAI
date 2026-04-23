#!/usr/bin/env python3
"""CLI for the SecurityAI training dataset generation pipeline.

Usage:
    cd backend
    source .venv/bin/activate
    python generate_dataset.py                       # defaults
    python generate_dataset.py --n-pairs 4           # 4 QA pairs per chunk
    python generate_dataset.py --dry-run             # show stats, no API calls
    python generate_dataset.py --books-dir /path/to/pdfs

The ANTHROPIC_API_KEY must be set in backend/.env or as an environment variable.
Get your key at https://console.anthropic.com
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _dry_run(books_dir: Path, target_words: int) -> None:
    """Show chunk statistics without making any API calls."""
    import fitz
    from data_pipeline.cleaner import clean_page_text, is_mostly_code
    from data_pipeline.splitter import split_into_chunks

    pdf_paths = sorted(books_dir.glob("*.pdf"))
    if not pdf_paths:
        print(f"No PDFs found in {books_dir}")
        sys.exit(1)

    total_chunks = 0
    for path in pdf_paths:
        doc = fitz.open(str(path))
        chunks = 0
        for page in doc:
            cleaned = clean_page_text(page.get_text())
            if cleaned and not is_mostly_code(cleaned):
                chunks += len(split_into_chunks(cleaned, target_words=target_words))
        doc.close()
        print(f"  {path.name}: {chunks} chunks")
        total_chunks += chunks

    print(f"\nTotal chunks: {total_chunks}")
    print(f"Estimated QA pairs (×3): ~{total_chunks * 3}")
    print(f"Estimated cost (claude-haiku-4-5, with caching): ~${total_chunks * 0.003:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate SecurityAI fine-tuning dataset from PDF textbooks"
    )
    parser.add_argument(
        "--books-dir",
        type=Path,
        default=Path(__file__).parent.parent / "book_data",
        help="Directory containing PDF textbooks (default: ../book_data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "data" / "dataset",
        help="Output directory for JSONL files (default: data/dataset/)",
    )
    parser.add_argument(
        "--n-pairs",
        type=int,
        default=3,
        help="QA pairs to generate per chunk (default: 3)",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.15,
        help="Fraction held out for test set (default: 0.15)",
    )
    parser.add_argument(
        "--target-words",
        type=int,
        default=200,
        help="Target chunk size in words (default: 200)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Seconds between API calls (default: 0.3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show chunk statistics without making API calls",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show debug logs including cache hit stats",
    )
    args = parser.parse_args()
    _configure_logging(args.verbose)

    if args.dry_run:
        print(f"Dry run — scanning {args.books_dir}\n")
        _dry_run(args.books_dir, args.target_words)
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("sk-ant-..."):
        print(
            "ERROR: ANTHROPIC_API_KEY is not set.\n"
            "  1. Get your key at https://console.anthropic.com\n"
            "  2. Add it to backend/.env:  ANTHROPIC_API_KEY=sk-ant-...\n"
            "  3. Re-run this script."
        )
        sys.exit(1)

    from data_pipeline.pipeline import run_pipeline

    print(f"Books dir : {args.books_dir}")
    print(f"Output dir: {args.output_dir}")
    print(f"Pairs/chunk: {args.n_pairs}  |  Test ratio: {args.test_ratio}")
    print()

    try:
        stats = run_pipeline(
            books_dir=args.books_dir,
            output_dir=args.output_dir,
            api_key=api_key,
            n_pairs=args.n_pairs,
            test_ratio=args.test_ratio,
            target_words=args.target_words,
            request_delay=args.delay,
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted — partial results saved to raw_qa_pairs.jsonl")
        sys.exit(0)

    print("\n── Dataset generation complete ──")
    print(json.dumps(stats, indent=2))
    print(f"\nFiles written to: {args.output_dir}")
    print(f"  train.jsonl  → {stats['train_pairs']} examples")
    print(f"  test.jsonl   → {stats['test_pairs']} examples")
    print(f"  stats.json   → full breakdown")
    print("\nNext step: upload train.jsonl to Google Colab for QLoRA fine-tuning.")


if __name__ == "__main__":
    main()
