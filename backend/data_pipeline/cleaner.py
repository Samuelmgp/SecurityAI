"""Clean raw PDF page text by stripping headers, footers, and page noise."""
import re


# Patterns that identify non-content lines
_PAGE_NUMBER = re.compile(r'^\s*\d{1,4}\s*$')
_COPYRIGHT    = re.compile(r'copyright|©|\(c\)', re.IGNORECASE)
_CHAPTER_HDR  = re.compile(r'^(chapter|part|section|appendix)\s+\w', re.IGNORECASE)
_ALL_CAPS_SHORT = re.compile(r'^[A-Z0-9 \-_:]{3,50}$')

# Code detection heuristics
_CODE_KEYWORDS = re.compile(
    r'\b(def |class |import |#include|void |int |char |printf|return |if \(|for \(|while \(|public |private |static )\b'
)
_HIGH_INDENT = re.compile(r'^( {4}|\t)')


def clean_page_text(text: str) -> str:
    """Strip headers, footers, page numbers, and formatting noise from a PDF page."""
    lines = text.splitlines()

    # Drop pure page-number lines
    lines = [l for l in lines if not _PAGE_NUMBER.match(l)]

    # Drop copyright notices
    lines = [l for l in lines if not _COPYRIGHT.search(l)]

    # Trim short non-sentence lines from the top (running headers)
    while lines:
        stripped = lines[0].strip()
        if stripped and len(stripped) < 80 and not stripped.endswith(('.', '?', ':', ',')):
            if _ALL_CAPS_SHORT.match(stripped) or _CHAPTER_HDR.match(stripped):
                lines.pop(0)
                continue
        break

    # Trim short non-sentence lines from the bottom (running footers)
    while lines:
        stripped = lines[-1].strip()
        if stripped and len(stripped) < 80 and not stripped.endswith(('.', '?', ':', ',')):
            if _ALL_CAPS_SHORT.match(stripped) or _CHAPTER_HDR.match(stripped):
                lines.pop()
                continue
        break

    cleaned = '\n'.join(lines)

    # Collapse runs of 3+ blank lines into a single paragraph break
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    # Remove hyphenated line-breaks common in PDF extraction (e.g. "secu-\nrity")
    cleaned = re.sub(r'-\n(?=[a-z])', '', cleaned)

    return cleaned.strip()


def is_mostly_code(text: str) -> bool:
    """Return True if the text looks like a code listing rather than prose."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return False
    code_lines = sum(
        1 for l in lines
        if _HIGH_INDENT.match(l) or _CODE_KEYWORDS.search(l)
    )
    return (code_lines / len(lines)) > 0.5
