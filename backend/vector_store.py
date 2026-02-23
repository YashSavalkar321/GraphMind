"""
GraphMind Backend — Vector Store (CQRS Read-Model Extension)
=============================================================
Per-user in-memory embedding matrix for semantic (cosine) retrieval.
Follows the same singleton / lock pattern as memory_store.py.

Model : sentence-transformers/all-MiniLM-L6-v2  (384-dim, CPU)
Warm  : call ``warm_model()`` once during FastAPI lifespan.
Search: ``vector_search(user_id, query, top_k)`` — pure numpy dot product.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("graphmind.vector_store")

# ══════════════════════════════════════════════════════════════════════════════
# Embedding model (global singleton)
# ══════════════════════════════════════════════════════════════════════════════

_model: Any = None
_EMBED_DIM = 384  # all-MiniLM-L6-v2 output dimension


def warm_model() -> None:
    """Eager-load the sentence-transformers model. Call once at startup."""
    global _model
    if _model is not None:
        return
    t0 = time.perf_counter()
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        elapsed = (time.perf_counter() - t0) * 1_000
        logger.info("Embedding model loaded (all-MiniLM-L6-v2) in %.0fms", elapsed)
    except Exception as exc:
        logger.error("Failed to load embedding model: %s", exc)
        _model = None


def _embed_text(text: str) -> np.ndarray:
    """Embed a single string → L2-normalised 384-dim vector."""
    if _model is None:
        return np.zeros(_EMBED_DIM, dtype=np.float32)
    vec = _model.encode(text, normalize_embeddings=True, show_progress_bar=False)
    return vec.astype(np.float32)


def _embed_batch(texts: List[str]) -> np.ndarray:
    """Embed multiple strings → (N, 384) L2-normalised matrix."""
    if _model is None or not texts:
        return np.zeros((max(len(texts), 1), _EMBED_DIM), dtype=np.float32)
    vecs = _model.encode(texts, normalize_embeddings=True,
                         show_progress_bar=False, batch_size=64)
    return vecs.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# Per-user vector index
# ══════════════════════════════════════════════════════════════════════════════

class _UserVectors:
    """Holds a node_id → row mapping plus the dense numpy matrix."""
    __slots__ = ("ids", "matrix")

    def __init__(self) -> None:
        self.ids: List[str] = []
        self.matrix: Optional[np.ndarray] = None  # shape (N, 384)


_USER_VECTORS: Dict[str, _UserVectors] = {}
_VEC_LOCK = asyncio.Lock()


def _build_embed_text(props: dict) -> str:
    """Format the text to embed for a node. Returns '' if nothing useful."""
    display = (props.get("display") or "").strip()
    snippet = (props.get("snippet") or "").strip()
    if display and snippet:
        return f"{display}. {snippet}"
    return display or snippet or ""


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

async def load_user_vectors(
    user_id: str,
    graph_nodes: Dict[str, dict],
    neo4j_embeddings: Dict[str, List[float]],
    driver: Any = None,
) -> int:
    """
    Populate the per-user vector index from graph nodes.

    Parameters
    ----------
    graph_nodes : dict
        node_id → {display, snippet, ...} from _UserGraph.nodes
    neo4j_embeddings : dict
        node_id → embedding list loaded from Neo4j (may be empty for nodes
        that predate the vector store)
    driver : Any
        Neo4j driver — used to persist backfilled embeddings

    Returns
    -------
    int
        Number of nodes indexed.
    """
    if not graph_nodes:
        return 0

    t0 = time.perf_counter()

    ids: List[str] = []
    vectors: List[np.ndarray] = []
    needs_backfill: List[Tuple[str, np.ndarray]] = []

    # Separate nodes with existing embeddings vs. those needing backfill
    nodes_to_embed: List[Tuple[str, str]] = []  # (node_id, text)

    for node_id, props in graph_nodes.items():
        existing_emb = neo4j_embeddings.get(node_id)
        if existing_emb and len(existing_emb) == _EMBED_DIM:
            ids.append(node_id)
            vectors.append(np.array(existing_emb, dtype=np.float32))
        else:
            text = _build_embed_text(props)
            if text:
                nodes_to_embed.append((node_id, text))

    # Batch-embed nodes missing embeddings
    if nodes_to_embed:
        texts = [t for _, t in nodes_to_embed]
        embeddings = await asyncio.to_thread(_embed_batch, texts)
        for i, (node_id, _) in enumerate(nodes_to_embed):
            vec = embeddings[i]
            ids.append(node_id)
            vectors.append(vec)
            needs_backfill.append((node_id, vec))

    # Build matrix
    uv = _UserVectors()
    uv.ids = ids
    uv.matrix = np.vstack(vectors) if vectors else np.zeros((0, _EMBED_DIM), dtype=np.float32)

    async with _VEC_LOCK:
        _USER_VECTORS[user_id] = uv

    elapsed = (time.perf_counter() - t0) * 1_000
    logger.info(
        "Vector index loaded: user=%s nodes=%d backfilled=%d time=%.1fms",
        user_id, len(ids), len(needs_backfill), elapsed,
    )

    # Fire-and-forget: persist backfilled embeddings to Neo4j
    if needs_backfill and driver:
        asyncio.create_task(_persist_embeddings(driver, user_id, needs_backfill))

    return len(ids)


async def _persist_embeddings(
    driver: Any, user_id: str, items: List[Tuple[str, np.ndarray]]
) -> None:
    """Write computed embeddings back to Neo4j for durability."""
    _PERSIST_CYPHER = (
        "MATCH (n {name: toLower($name), user_id: $uid}) "
        "SET n.embedding = $embedding"
    )

    def _write() -> None:
        with driver.session() as session:
            for node_id, vec in items:
                try:
                    session.run(_PERSIST_CYPHER, {
                        "name": node_id,
                        "uid": user_id,
                        "embedding": vec.tolist(),
                    })
                except Exception as exc:
                    logger.warning("Persist embedding failed (%s): %s", node_id, exc)

    try:
        await asyncio.to_thread(_write)
        logger.info("Backfilled %d embeddings to Neo4j for user=%s", len(items), user_id)
    except Exception as exc:
        logger.warning("Embedding backfill failed (non-fatal): %s", exc)


def vector_search(
    user_id: str, query: str, top_k: int = 15
) -> List[Tuple[str, float]]:
    """
    Cosine similarity search over the user's in-memory vectors.

    Returns list of (node_id, score) sorted by descending similarity.
    Score range: -1.0 to 1.0 (vectors are L2-normalised → dot = cosine).
    """
    uv = _USER_VECTORS.get(user_id)
    if uv is None or uv.matrix is None or len(uv.ids) == 0:
        return []

    query_vec = _embed_text(query)
    if np.linalg.norm(query_vec) < 1e-9:
        return []

    # Cosine similarity = dot product (vectors are already L2-normalised)
    scores = uv.matrix @ query_vec  # shape (N,)

    # Get top-k indices
    k = min(top_k, len(uv.ids))
    top_indices = np.argpartition(scores, -k)[-k:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

    results = []
    for idx in top_indices:
        score = float(scores[idx])
        if score > 0.35:  # minimum similarity threshold
            results.append((uv.ids[idx], score))

    return results


async def update_user_vectors(user_id: str, new_nodes: List[dict]) -> None:
    """
    Incrementally add new node embeddings to the user's vector index.

    Parameters
    ----------
    new_nodes : list of dict
        Each dict has node_id, display, snippet, and optionally embedding.
    """
    uv = _USER_VECTORS.get(user_id)
    if uv is None:
        return

    # Collect nodes that need embedding
    to_embed: List[Tuple[str, str]] = []
    pre_embedded: List[Tuple[str, np.ndarray]] = []

    for n in new_nodes:
        nid = (n.get("node_id") or n.get("name") or "").lower()
        if not nid or nid in uv.ids:
            continue  # skip duplicates

        # Check if embedding was already computed (e.g., by worker)
        existing_emb = n.get("embedding")
        if existing_emb and len(existing_emb) == _EMBED_DIM:
            pre_embedded.append((nid, np.array(existing_emb, dtype=np.float32)))
        else:
            text = _build_embed_text(n)
            if text:
                to_embed.append((nid, text))

    if not to_embed and not pre_embedded:
        return

    # Batch-embed new nodes
    new_ids: List[str] = []
    new_vecs: List[np.ndarray] = []

    for nid, vec in pre_embedded:
        new_ids.append(nid)
        new_vecs.append(vec)

    if to_embed:
        texts = [t for _, t in to_embed]
        embeddings = await asyncio.to_thread(_embed_batch, texts)
        for i, (nid, _) in enumerate(to_embed):
            new_ids.append(nid)
            new_vecs.append(embeddings[i])

    if not new_vecs:
        return

    new_matrix = np.vstack(new_vecs)

    async with _VEC_LOCK:
        uv = _USER_VECTORS.get(user_id)
        if uv is None:
            return
        uv.ids.extend(new_ids)
        if uv.matrix is not None and uv.matrix.shape[0] > 0:
            uv.matrix = np.vstack([uv.matrix, new_matrix])
        else:
            uv.matrix = new_matrix

    logger.info("Vector index updated: user=%s +%d nodes (total=%d)",
                user_id, len(new_ids), len(uv.ids))


def drop_user_vectors(user_id: str) -> None:
    """Remove user's vector index from RAM."""
    _USER_VECTORS.pop(user_id, None)


def get_node_embedding(node_props: dict) -> Optional[List[float]]:
    """
    Compute and return the embedding for a single node.
    Used by worker.py to get embeddings for Neo4j persistence.
    Returns None if text is empty or model not loaded.
    """
    text = _build_embed_text(node_props)
    if not text or _model is None:
        return None
    vec = _embed_text(text)
    return vec.tolist()
