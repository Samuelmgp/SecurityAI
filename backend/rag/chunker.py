"""Split raw text into overlapping word-count chunks, preserving paragraph boundaries where possible."""
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    word_start: int
    word_end: int


def split_text(text: str, chunk_size: int = 400, overlap: int = 60) -> list[Chunk]:
    """Split text into chunks of ~chunk_size words with overlap words of context carry-over."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    words: list[str] = []
    for para in paragraphs:
        words.extend(para.split())
        words.append("\n\n")  # paragraph sentinel preserved in word stream

    chunks: list[Chunk] = []
    i = 0
    total = len(words)

    while i < total:
        end = min(i + chunk_size, total)
        chunk_words = words[i:end]
        text_out = " ".join(w for w in chunk_words if w != "\n\n").strip()
        if text_out:
            chunks.append(Chunk(text=text_out, word_start=i, word_end=end))
        i += chunk_size - overlap

    return chunks
