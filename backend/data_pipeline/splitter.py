"""Paragraph-aware text splitter.

Splits on paragraph boundaries (double newlines) and merges small paragraphs
together until they approach the target word count.  Never cuts mid-paragraph.
"""


def split_into_chunks(
    text: str,
    target_words: int = 200,
    min_words: int = 40,
) -> list[str]:
    """Split text into ~target_words-word chunks aligned to paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks: list[str] = []
    current_parts: list[str] = []
    current_words = 0

    for para in paragraphs:
        word_count = len(para.split())

        # Single paragraph already exceeds target — emit it alone
        if word_count >= target_words and not current_parts:
            chunks.append(para)
            continue

        # Adding this paragraph would overflow — flush current buffer first
        if current_words + word_count > target_words and current_parts:
            chunk = '\n\n'.join(current_parts)
            if len(chunk.split()) >= min_words:
                chunks.append(chunk)
            current_parts = []
            current_words = 0

        current_parts.append(para)
        current_words += word_count

    # Flush remaining
    if current_parts:
        chunk = '\n\n'.join(current_parts)
        if len(chunk.split()) >= min_words:
            chunks.append(chunk)

    return chunks
