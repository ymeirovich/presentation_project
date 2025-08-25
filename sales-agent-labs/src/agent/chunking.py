from __future__ import annotations
from typing import List


def split_paragraphs(text: str) -> List[str]:
    # Split on blank lines; keep paragraph integrity where possible
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts or [text.strip()]


def chunk_by_words(paragraphs: List[str], max_words: int = 350) -> List[str]:
    """
    Greedy pack paragraphs into chunks up to ~max_words.
    Keeping paragraphs intact preserves context while staying under limits.
    """
    chunks: List[str] = []
    current: list[str] = []
    count = 0

    for p in paragraphs:
        w = len(p.split())
        if w > max_words:
            # If a single paragraph is enormous, hard-split it by words
            words = p.split()
            for i in range(0, len(words), max_words):
                sub = " ".join(words[i : i + max_words])
                if current:
                    chunks.append("\n\n".join(current))
                    current, count = [], 0
                chunks.append(sub)
            continue
        if count + w <= max_words:
            current.append(p)
            count += w
        else:
            if current:
                chunks.append("\n\n".join(current))
            current, count = [p], w

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_text(text: str, max_words: int = 350) -> List[str]:
    """
    Public helper: paragraphs first, then word-capped chunks.
    """
    return chunk_by_words(split_paragraphs(text), max_words=max_words)
