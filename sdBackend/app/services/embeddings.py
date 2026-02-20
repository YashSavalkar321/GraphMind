"""
GraphMind — Local embedding via fastembed.
Uses BAAI/bge-small-en-v1.5 (384-dim, ~33M params, very fast on CPU).
"""

import logging
from typing import List

from fastembed import TextEmbedding

from app.config import settings

logger = logging.getLogger(__name__)

_model: TextEmbedding | None = None


def get_model() -> TextEmbedding:
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s' …", settings.embedding_model)
        _model = TextEmbedding(model_name=settings.embedding_model)
        logger.info("Embedding model loaded")
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts. Returns list of float vectors."""
    model = get_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]
