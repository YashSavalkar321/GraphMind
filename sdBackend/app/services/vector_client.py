"""
GraphMind — Qdrant vector DB client.
Stores embedded text chunks with user_id isolation.
"""

import logging
from typing import Any, Dict, List, Optional
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.config import settings

logger = logging.getLogger(__name__)


class VectorClient:
    """Thin wrapper around the Qdrant Python client."""

    def __init__(self) -> None:
        self._client: Optional[QdrantClient] = None
        self._collection = settings.qdrant_collection
        self._vector_size = 384  # BAAI/bge-small-en-v1.5 output dimension

    async def connect(self) -> None:
        # Try remote Qdrant first, fall back to local file-based mode
        try:
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=10,
            )
            # Test connection
            self._client.get_collections()
            logger.info("Connected to remote Qdrant at %s:%s", settings.qdrant_host, settings.qdrant_port)
        except Exception as e:
            logger.warning("Remote Qdrant unavailable (%s), using local file-based storage", e)
            import os
            storage_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".qdrant_local")
            os.makedirs(storage_path, exist_ok=True)
            self._client = QdrantClient(path=storage_path)
            logger.info("Qdrant local storage at %s", storage_path)

        # Create collection if not exists
        collections = self._client.get_collections().collections
        exists = any(c.name == self._collection for c in collections)
        if not exists:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._vector_size, distance=Distance.COSINE
                ),
            )
            logger.info("Created Qdrant collection '%s'", self._collection)
        else:
            logger.info("Qdrant collection '%s' already exists", self._collection)

    async def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("Qdrant connection closed")

    # ────────────────────────────────────────────────────────────
    #  Write
    # ────────────────────────────────────────────────────────────

    def upsert_chunks(
        self,
        user_id: str,
        chunks: List[Dict[str, Any]],
        vectors: List[List[float]],
    ) -> int:
        """
        Insert text chunks into Qdrant.
        Each chunk dict must have: chunk_text, memory_id (node id), doc_source, title.
        Returns the number of points upserted.
        """
        points = []
        for chunk, vector in zip(chunks, vectors):
            point_id = uuid.uuid4().hex
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "user_id": user_id,
                        "chunk_text": chunk["chunk_text"],
                        "memory_id": chunk.get("memory_id", ""),
                        "doc_source": chunk.get("doc_source", ""),
                        "title": chunk.get("title", ""),
                    },
                )
            )

        if points:
            self._client.upsert(
                collection_name=self._collection, points=points
            )
        return len(points)

    # ────────────────────────────────────────────────────────────
    #  Read — Similarity search
    # ────────────────────────────────────────────────────────────

    def search(
        self,
        user_id: str,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search filtered by user_id.
        Returns list of {chunk_text, memory_id, title, score}.
        """
        from qdrant_client.models import QueryResponse
        try:
            # Modern qdrant-client (>=1.12) uses query_points
            results = self._client.query_points(
                collection_name=self._collection,
                query=query_vector,
                limit=top_k,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id", match=MatchValue(value=user_id)
                        )
                    ]
                ),
            )
            points = results.points if hasattr(results, 'points') else results
            return [
                {
                    "chunk_text": hit.payload.get("chunk_text", ""),
                    "memory_id": hit.payload.get("memory_id", ""),
                    "title": hit.payload.get("title", ""),
                    "doc_source": hit.payload.get("doc_source", ""),
                    "score": hit.score,
                }
                for hit in points
            ]
        except Exception:
            # Fallback to legacy .search() for older versions
            results = self._client.search(
                collection_name=self._collection,
                query_vector=query_vector,
                limit=top_k,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id", match=MatchValue(value=user_id)
                        )
                    ]
                ),
            )
            return [
                {
                    "chunk_text": hit.payload.get("chunk_text", ""),
                    "memory_id": hit.payload.get("memory_id", ""),
                    "title": hit.payload.get("title", ""),
                    "doc_source": hit.payload.get("doc_source", ""),
                    "score": hit.score,
                }
                for hit in results
            ]


# Singleton
vector_client = VectorClient()
