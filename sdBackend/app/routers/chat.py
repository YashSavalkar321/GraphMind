"""
GraphMind — POST /chat
Hybrid parallel retrieval → LLM generation.
Includes semantic query caching (Redis) and mindmap cache invalidation.
"""

import json
import logging

from fastapi import APIRouter, HTTPException

from app.models import ChatRequest, ChatResponse
from app.services.retrieval import hybrid_retrieve, generate_answer
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    1. Check Redis semantic cache for identical query
    2. Parallel retrieval from Qdrant + Neo4j  (timed with perf_counter)
    3. Hybrid fusion → context assembly
    4. LLM generation
    5. Cache the response in Redis
    6. Invalidate mindmap cache (chat can create new graph links)
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # ── Semantic cache: exact query hit? ──
    cached = await redis_client.get_query_cache(req.user_id, req.query)
    if cached:
        logger.info("Semantic cache HIT for user %s", req.user_id)
        data = json.loads(cached)
        return ChatResponse(**data)

    # ── Retrieval (timed) ──
    retrieval_time_ms, context, citations = await hybrid_retrieve(
        user_id=req.user_id, query=req.query
    )
    logger.info(
        "Retrieval complete: %.1f ms, %d citations", retrieval_time_ms, len(citations)
    )

    # ── LLM Generation (NOT timed) ──
    answer = await generate_answer(
        query=req.query, context=context, citations=citations
    )

    response = ChatResponse(
        response=answer,
        retrieval_time_ms=retrieval_time_ms,
        memory_citations=citations,
    )

    # ── Cache this response for identical future queries ──
    try:
        await redis_client.set_query_cache(
            req.user_id, req.query, response.model_dump_json()
        )
    except Exception as e:
        logger.warning("Failed to cache query response: %s", e)

    # ── Invalidate mindmap cache (new data may have been written) ──
    await redis_client.invalidate_mindmap(req.user_id)

    return response
