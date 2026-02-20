"""
GraphMind — POST /chat
Hybrid parallel retrieval → LLM generation.
The retrieval_time_ms is measured with perf_counter wrapping ONLY the DB operations.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.models import ChatRequest, ChatResponse
from app.services.retrieval import hybrid_retrieve, generate_answer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    1. Parallel retrieval from Qdrant + Neo4j  (timed with perf_counter)
    2. Hybrid fusion → context assembly         (still inside the timer)
    3. LLM generation                            (OUTSIDE the timer)
    4. Return response + retrieval_time_ms + citations
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

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

    return ChatResponse(
        response=answer,
        retrieval_time_ms=retrieval_time_ms,
        memory_citations=citations,
    )
