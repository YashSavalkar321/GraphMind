"""
GraphMind — Hybrid parallel retrieval engine.
Runs vector search + graph neighborhood lookup in parallel,
then fuses results for the LLM context window.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Tuple

from app.models import MemoryCitation
from app.services.neo4j_client import neo4j_client
from app.services.vector_client import vector_client
from app.services.embeddings import embed_query
from app.services.extraction import extract_entity_from_query
from app.services.llm_client import llm_generate

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  Chat system prompt
# ═══════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = """You are GraphMind, an AI assistant that answers questions based on the user's personal knowledge graph and ingested documents.

RULES:
1. Answer ONLY using the provided context. If the context doesn't contain relevant info, say so honestly.
2. When referencing information, naturally cite the source node using its node_id in square brackets like [node_id].
3. Use markdown formatting: **bold** for key terms, bullet points for lists.
4. Be concise but thorough. Aim for 2-4 paragraphs.
5. If multiple memory citations are relevant, reference all of them.
6. Never fabricate information not present in the context.

CONTEXT FROM MEMORY:
{context}
"""


# ═══════════════════════════════════════════════════════════
#  Hybrid Retrieval Pipeline
# ═══════════════════════════════════════════════════════════

async def hybrid_retrieve(
    user_id: str, query: str
) -> Tuple[float, str, List[MemoryCitation]]:
    """
    Parallel retrieval from Vector DB + Graph DB.
    
    Returns:
        retrieval_time_ms: time spent on DB fetch + context assembly
        context_text: assembled context string for the LLM
        citations: list of MemoryCitation for the frontend
    """
    t_start = time.perf_counter()

    # ── Parallel: Vector search + Graph neighborhood ──
    vector_task = asyncio.get_event_loop().run_in_executor(
        None, _vector_search, user_id, query
    )
    graph_task = _graph_search(user_id, query)

    vector_results, graph_results = await asyncio.gather(
        vector_task, graph_task, return_exceptions=True
    )

    # Handle exceptions gracefully
    if isinstance(vector_results, Exception):
        logger.error("Vector search failed: %s", vector_results)
        vector_results = []
    if isinstance(graph_results, Exception):
        logger.error("Graph search failed: %s", graph_results)
        graph_results = []

    # ── Hybrid Fusion: deduplicate by memory_id ──
    seen_ids = set()
    fused: List[Dict[str, Any]] = []

    # Vector results first (higher semantic relevance)
    for item in vector_results:
        mid = item.get("memory_id", "")
        if mid and mid not in seen_ids:
            seen_ids.add(mid)
            fused.append(item)

    # Then graph results
    for item in graph_results:
        mid = item.get("id", "")
        if mid and mid not in seen_ids:
            seen_ids.add(mid)
            fused.append({
                "memory_id": mid,
                "title": item.get("name", ""),
                "chunk_text": item.get("description", ""),
                "node_type": item.get("node_type", ""),
            })

    # ── Build context string ──
    context_parts = []
    citations: List[MemoryCitation] = []

    for item in fused[:8]:  # Cap at 8 context items
        node_id = item.get("memory_id", "")
        title = item.get("title", "Unknown")
        text = item.get("chunk_text", "")
        if text:
            context_parts.append(f"[{node_id}] {title}: {text}")
            citations.append(
                MemoryCitation(
                    node_id=node_id,
                    title=title,
                    snippet=text[:150],
                )
            )

    context_text = "\n\n".join(context_parts) if context_parts else "No relevant memory found."

    t_end = time.perf_counter()
    retrieval_time_ms = round((t_end - t_start) * 1000, 1)

    return retrieval_time_ms, context_text, citations


def _vector_search(user_id: str, query: str) -> List[Dict[str, Any]]:
    """Synchronous vector search (runs in executor)."""
    query_vector = embed_query(query)
    return vector_client.search(user_id=user_id, query_vector=query_vector, top_k=5)


async def _graph_search(user_id: str, query: str) -> List[Dict[str, Any]]:
    """Extract entity from query, then fetch 1-hop neighborhood from Neo4j."""
    entity = await extract_entity_from_query(query)
    if not entity:
        return []
    return await neo4j_client.get_neighborhood(user_id=user_id, entity_name=entity)


# ═══════════════════════════════════════════════════════════
#  Generate Answer
# ═══════════════════════════════════════════════════════════

async def generate_answer(
    query: str, context: str, citations: List[MemoryCitation]
) -> str:
    """Call the LLM with retrieved context and return the answer."""
    system = CHAT_SYSTEM_PROMPT.format(context=context)

    try:
        answer = await llm_generate(
            system_prompt=system,
            user_prompt=query,
            temperature=0.4,
            max_tokens=1500,
        )
        return answer
    except Exception as e:
        logger.error("LLM generation failed: %s", e)
        # Graceful fallback
        if citations:
            parts = [f"Based on your memory, here's what I found:\n"]
            for c in citations:
                parts.append(f"- **{c.title}**: {c.snippet}")
            return "\n".join(parts)
        return (
            "I encountered an issue generating a response. "
            "Please check your LLM API key configuration."
        )
