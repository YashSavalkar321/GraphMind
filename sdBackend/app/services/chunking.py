"""
GraphMind — Text chunking utility.
Splits text into overlapping chunks for embedding.
"""

import re
from typing import List


def chunk_text(
    text: str,
    max_chunk_size: int = 500,
    overlap: int = 50,
) -> List[str]:
    """
    Split text into chunks of roughly max_chunk_size characters.
    Uses sentence boundaries when possible, with overlap for context.
    """
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if not sentences:
        return [text]

    chunks: List[str] = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence would exceed limit, save current chunk
        if current_chunk and len(current_chunk) + len(sentence) + 1 > max_chunk_size:
            chunks.append(current_chunk.strip())
            # Keep overlap from end of current chunk
            if overlap > 0:
                words = current_chunk.split()
                overlap_text = " ".join(words[-overlap // 5 :]) if len(words) > overlap // 5 else ""
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # If text is too short for even one chunk, return as-is
    if not chunks:
        chunks = [text]

    return chunks
