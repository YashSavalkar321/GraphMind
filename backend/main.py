"""
GraphMind — FastAPI Application
=================================
Member 2 (Backend Lead) deliverables:
- All endpoints with Clerk JWT auth
- Full OpenAPI/Swagger documentation
- Proper error responses
- Learning Path Planner endpoints
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import JWT_ALGORITHM, JWT_SECRET, get_current_user
from backend.database import get_db
from fastapi.responses import StreamingResponse
from fastapi import BackgroundTasks
from backend.llm_service import generate_answer, generate_answer_stream, generate_learning_roadmap
from backend.memory_ops import (
    get_user_graph,
    get_user_profile,
    ingest_to_graph,
    retrieve_from_graph,
)
from backend.memory_store import (
    assemble_context,
    bfs_subgraph,
    drop_user_session,
    get_graph_stats,
    init_user_session,
    scan_query,
    _USER_GRAPHS,
)
from backend.worker import extract_and_sync_graph
from backend.vector_store import vector_search as _vector_search, warm_model as _warm_embedding_model
from backend.models import (
    ChatRequest,
    ChatResponse,
    ChatMessagePayload,
    ChatSessionResponse,
    IngestRequest,
    IngestResponse,
    LearningRoadmapResponse,
    LoginRequest,
    LoginResponse,
    MemoryCitation,
    MindmapResponse,
    ReactFlowEdge,
    ReactFlowMindmapResponse,
    ReactFlowNode,
    ReactFlowNodeData,
    ReactFlowPosition,
    RoadmapRequest,
    RoadmapStep,
    SaveChatRequest,
    SignupRequest,
    SignupResponse,
    UserProfileResponse,
)

# ── Logging ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
)
logger = logging.getLogger("graphmind.api")


# ── Auth Utilities (password hashing + JWT) ──────────────────────

def _hash_password(password: str) -> str:
    """SHA-256 hash with a random salt (hex-encoded)."""
    salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def _verify_password(plain: str, stored: str) -> bool:
    """Verify a plain password against the stored salt:hash."""
    try:
        salt, h = stored.split(":", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == h
    except Exception:
        return False


def _create_jwt(user_id: str, name: str) -> str:
    """Create a signed HS256 JWT valid for 24 hours."""
    import jwt as pyjwt
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": user_id,
        "name": name,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── In-memory user store (swap for a real DB in production) ──────
# Schema: { email.lower(): { user_id, name, email, hashed_password } }
_user_store: dict = {}


# ── Lifespan ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop the Neo4j driver, set up DB constraints, warm embedding model."""
    db = get_db()
    db.init_driver()
    db.setup_constraints()
    # Expose the raw Neo4j driver on app.state so background workers can use it
    app.state.neo4j_driver = db._driver
    # Eager-load embedding model for hybrid retrieval
    _warm_embedding_model()
    logger.info("GraphMind backend started ✓  (CQRS in-memory engine + hybrid retrieval ready)")
    yield
    db.close_driver()
    app.state.neo4j_driver = None
    logger.info("GraphMind backend stopped.")


# ── Hybrid Retrieval Engine ────────────────────────────────────

def _hybrid_retrieve(user_id: str, query: str) -> dict:
    """
    Hybrid retrieval: graph (Aho-Corasick) + vector (cosine) seeds → BFS → merge + re-rank.

    Returns
    -------
    dict with keys:
        context, retrieval_time_ms, memory_citations, entities_found,
        broad_query, total_facts_scanned, facts_selected, source
    """
    import time as _time
    t0 = _time.perf_counter()

    # ── 1. Parallel seed collection ── (both are pure CPU, < 3ms total)
    graph_seed_ids  = scan_query(user_id, query)       # Aho-Corasick exact match
    vector_results  = _vector_search(user_id, query, top_k=15)  # cosine similarity
    vector_seed_ids = [nid for nid, _ in vector_results]
    vector_scores   = {nid: score for nid, score in vector_results}

    # ── 2. Determine retrieval path ──
    has_graph  = len(graph_seed_ids) > 0
    has_vector = len(vector_seed_ids) > 0

    if not has_graph and not has_vector:
        # Broad query — no seeds at all
        broad_query = True
        # Use full user subgraph (grab everything up to max_nodes)
        graph = _USER_GRAPHS.get(user_id)
        if graph and graph.nodes:
            all_ids = list(graph.nodes.keys())[:80]
            sub_nodes, sub_edges = bfs_subgraph(user_id, all_ids, max_hops=0, max_nodes=80)
        else:
            sub_nodes, sub_edges = [], []

    elif has_graph and not has_vector:
        # Graph-only path (current behaviour)
        broad_query = False
        sub_nodes, sub_edges = bfs_subgraph(user_id, graph_seed_ids, max_hops=2, max_nodes=80)

    elif not has_graph and has_vector:
        # Vector-only path (pure semantic)
        broad_query = False
        sub_nodes, sub_edges = bfs_subgraph(user_id, vector_seed_ids, max_hops=2, max_nodes=80)

    else:
        # ── Full hybrid merge ──
        broad_query = False

        graph_set  = set(graph_seed_ids)
        vector_set = set(vector_seed_ids)

        # Weighted merge: graph=1.0, vector=0.6, overlap=1.6
        merged_scores: Dict[str, float] = {}
        for nid in graph_set:
            merged_scores[nid] = merged_scores.get(nid, 0.0) + 1.0
        for nid in vector_set:
            vscore = vector_scores.get(nid, 0.5) * 0.6  # scale vector score
            merged_scores[nid] = merged_scores.get(nid, 0.0) + vscore

        # Sort by merged score descending, take top seeds
        ranked_seeds = sorted(merged_scores.keys(),
                              key=lambda x: merged_scores[x], reverse=True)[:30]

        sub_nodes, sub_edges = bfs_subgraph(user_id, ranked_seeds, max_hops=2, max_nodes=80)

    context = assemble_context(sub_nodes, sub_edges)
    retrieval_ms = (_time.perf_counter() - t0) * 1_000

    # ── 3. Build memory citations ──
    all_seeds = set(graph_seed_ids) | set(vector_seed_ids)
    memory_citations = [
        {"node_id": n["node_id"],
         "title":   n.get("display") or n["node_id"],
         "snippet": n.get("snippet", "")}
        for n in sub_nodes if n["node_id"] in all_seeds
    ][:6]

    entities_found = list(all_seeds)

    # Determine source label
    if has_graph and has_vector:
        source = "hybrid"
    elif has_vector:
        source = "vector"
    elif has_graph:
        source = "graph"
    else:
        source = "broad"

    logger.info(
        "Hybrid retrieve: user=%s graph_seeds=%d vector_seeds=%d "
        "merged_nodes=%d time=%.2fms source=%s",
        user_id, len(graph_seed_ids), len(vector_seed_ids),
        len(sub_nodes), retrieval_ms, source,
    )

    return {
        "context":             context,
        "retrieval_time_ms":   round(retrieval_ms, 3),
        "memory_citations":    memory_citations,
        "broad_query":         broad_query,
        "entities_found":      entities_found,
        "total_facts_scanned": len(sub_nodes),
        "facts_selected":      len(sub_nodes),
        "source":              source,
    }


# ── FastAPI Application ─────────────────────────────────────────

app = FastAPI(
    title="GraphMind API",
    description=(
        "**User-Centric Long-Term Memory Assistant** powered by Graph RAG.\n\n"
        "- **Clerk Authentication**: All endpoints require a valid JWT token\n"
        "- **Per-User Isolation**: Each user's knowledge graph is completely separate\n"
        "- **Learning Path Planner**: Generate personalized learning roadmaps\n"
        "- **Real-time Memory**: Chat messages auto-ingest into the graph\n\n"
        "Use `/docs` to explore the API interactively."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check (public) ──────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Health Check",
    description="Public endpoint. Returns backend and Neo4j status.",
    response_model=dict,
    responses={
        200: {
            "description": "Backend is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "neo4j": True,
                        "version": "2.0.0",
                    }
                }
            },
        }
    },
)
async def health():
    db = get_db()
    neo4j_ok = db.verify_connectivity()
    return {
        "status": "ok",
        "neo4j": neo4j_ok,
        "version": "2.0.0",
        "active_sessions": len(_USER_GRAPHS),
        "architecture": "in-memory-cqrs-sse",
    }


# ── Auth: Signup ───────────────────────────────────────────────

@app.post(
    "/auth/signup",
    response_model=SignupResponse,
    tags=["Auth"],
    summary="Register a new user",
    status_code=201,
    responses={409: {"description": "Email already registered"}},
)
async def signup(request: SignupRequest):
    """Register a new user and return a JWT token."""
    email_key = request.email.lower()
    if email_key in _user_store:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    hashed = _hash_password(request.password)

    _user_store[email_key] = {
        "user_id": user_id,
        "name": request.name,
        "email": email_key,
        "hashed_password": hashed,
    }

    # Create root User node in Neo4j
    try:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        db.execute_write(
            "MERGE (u:User {user_id: $uid}) "
            "ON CREATE SET u.name = $name, u.created_at = $now",
            {"uid": user_id, "name": request.name, "now": now},
        )
    except Exception as e:
        logger.warning("Could not create User node in Neo4j (non-fatal): %s", e)

    token = _create_jwt(user_id, request.name)
    logger.info("New user registered: %s (%s)", request.name, user_id)
    # Kick off session warm-up so /chat/stream is zero-latency from first message
    driver = getattr(app.state, "neo4j_driver", None)
    if driver:
        asyncio.create_task(init_user_session(user_id, driver))
    return SignupResponse(user_id=user_id, name=request.name, email=email_key, token=token)


# ── Auth: Login ────────────────────────────────────────────────

@app.post(
    "/auth/login",
    response_model=LoginResponse,
    tags=["Auth"],
    summary="Login and get JWT",
    responses={401: {"description": "Invalid credentials"}},
)
async def login(request: LoginRequest):
    """Authenticate an existing user and return a JWT token."""
    user = _user_store.get(request.email.lower())
    if not user or not _verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_jwt(user["user_id"], user["name"])
    logger.info("User logged in: %s (%s)", user["name"], user["user_id"])
    # Warm up in-memory session so /chat/stream reads from RAM immediately
    driver = getattr(app.state, "neo4j_driver", None)
    if driver:
        asyncio.create_task(init_user_session(user["user_id"], driver))
    return LoginResponse(
        user_id=user["user_id"],
        name=user["name"],
        email=user["email"],
        token=token,
    )


# ── Session Init (warm-up) ────────────────────────────────────

@app.post(
    "/session/init",
    tags=["Memory"],
    summary="Warm up in-memory session",
    description=(
        "Load the user's full graph from Neo4j into RAM once. "
        "After this call, /chat/stream retrieval is zero-database (< 15ms). "
        "Called automatically on login/signup, but can be called manually."
    ),
)
async def session_init(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    from backend.models import SessionInitResponse
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(status_code=503, detail="Neo4j driver not available.")
    nodes_loaded, auto_keys, init_ms = await init_user_session(user_id, driver)
    return SessionInitResponse(
        user_id=user_id,
        nodes_loaded=nodes_loaded,
        automaton_keys=auto_keys,
        init_time_ms=round(init_ms, 2),
    )


# ── Chat Persistence: CRUD ────────────────────────────────────

@app.get(
    "/chats",
    response_model=List[ChatSessionResponse],
    tags=["Chat History"],
    summary="List all chat sessions",
    description="Returns all persisted chat sessions for the authenticated user, ordered by updatedAt descending.",
    responses={401: {"description": "Not authenticated"}},
)
async def list_chats(
    user_id: str = Depends(get_current_user),
):
    """Fetch all chat sessions for the current user from Neo4j."""
    import json as _json
    try:
        db = get_db()
        records = db.execute_query(
            "MATCH (cs:ChatSession {user_id: $uid}) "
            "RETURN cs.chat_id AS chat_id, cs.title AS title, "
            "       cs.pinned AS pinned, cs.messages AS messages, "
            "       cs.createdAt AS createdAt, cs.updatedAt AS updatedAt "
            "ORDER BY cs.pinned DESC, cs.updatedAt DESC",
            {"uid": user_id},
        )
        sessions = []
        for r in records:
            try:
                msgs = _json.loads(r.get("messages") or "[]")
            except Exception:
                msgs = []
            sessions.append(ChatSessionResponse(
                chat_id=r["chat_id"],
                title=r.get("title", "New Chat"),
                pinned=bool(r.get("pinned", False)),
                messages=msgs,
                createdAt=r.get("createdAt", ""),
                updatedAt=r.get("updatedAt", ""),
            ))
        return sessions
    except Exception as exc:
        logger.exception("List chats failed")
        raise HTTPException(status_code=500, detail=f"List chats error: {exc}")


@app.post(
    "/chats",
    response_model=ChatSessionResponse,
    tags=["Chat History"],
    summary="Save or update a chat session",
    description="Upserts a chat session (by chat_id) into Neo4j.",
    responses={401: {"description": "Not authenticated"}},
)
async def save_chat(
    request: SaveChatRequest,
    user_id: str = Depends(get_current_user),
):
    """Upsert a chat session into Neo4j."""
    import json as _json
    try:
        db = get_db()
        messages_json = _json.dumps(
            [m.model_dump() for m in request.messages],
            ensure_ascii=False,
        )
        now = datetime.now(timezone.utc).isoformat()
        db.execute_write(
            "MERGE (cs:ChatSession {chat_id: $cid}) "
            "ON CREATE SET cs.user_id = $uid, cs.createdAt = $createdAt "
            "SET cs.title = $title, cs.pinned = $pinned, "
            "    cs.messages = $messages, cs.updatedAt = $now",
            {
                "cid": request.chat_id,
                "uid": user_id,
                "title": request.title,
                "pinned": request.pinned,
                "messages": messages_json,
                "createdAt": request.createdAt or now,
                "now": now,
            },
        )
        return ChatSessionResponse(
            chat_id=request.chat_id,
            title=request.title,
            pinned=request.pinned,
            messages=[m.model_dump() for m in request.messages],
            createdAt=request.createdAt or now,
            updatedAt=now,
        )
    except Exception as exc:
        logger.exception("Save chat failed")
        raise HTTPException(status_code=500, detail=f"Save chat error: {exc}")


@app.delete(
    "/chats/{chat_id}",
    tags=["Chat History"],
    summary="Delete a chat session",
    description="Permanently removes a chat session from Neo4j.",
    responses={401: {"description": "Not authenticated"}},
)
async def delete_chat(
    chat_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a chat session from Neo4j."""
    try:
        db = get_db()
        db.execute_write(
            "MATCH (cs:ChatSession {chat_id: $cid, user_id: $uid}) "
            "DETACH DELETE cs",
            {"cid": chat_id, "uid": user_id},
        )
        return {"status": "ok", "chat_id": chat_id}
    except Exception as exc:
        logger.exception("Delete chat failed")
        raise HTTPException(status_code=500, detail=f"Delete chat error: {exc}")


# ── Chat (authenticated) ──────────────────────────────────────

@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Memory"],
    summary="Chat with Memory",
    description=(
        "Send a message. The system retrieves relevant memories, "
        "generates a context-aware answer, and auto-ingests the message "
        "into the user's knowledge graph."
    ),
    responses={
        401: {"description": "Not authenticated"},
        503: {"description": "LLM provider unavailable"},
    },
)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    """Chat with memory — hybrid retrieve, answer, then auto-ingest."""
    # Allow user_id override from request body (frontend sends it there)
    effective_user_id = request.user_id or user_id
    try:
        # ── Lazy-init: load session into RAM if not already warm ──
        if effective_user_id not in _USER_GRAPHS:
            db = get_db()
            _driver = db._driver
            if _driver:
                try:
                    await init_user_session(effective_user_id, _driver)
                    logger.info("Lazy session init for /chat user=%s", effective_user_id)
                except Exception as init_exc:
                    logger.warning("Session init failed (non-fatal): %s", init_exc)

        # ── Retrieve context ──
        if effective_user_id in _USER_GRAPHS:
            # Hybrid retrieval (in-memory CQRS + vector search)
            retrieval = _hybrid_retrieve(effective_user_id, request.query)
            context = retrieval["context"]
            memory_citations = [
                MemoryCitation(
                    node_id=c["node_id"], title=c["title"], snippet=c["snippet"]
                ) for c in retrieval["memory_citations"]
            ]
            retrieval_time_ms = retrieval["retrieval_time_ms"]
            entities_found = retrieval["entities_found"]
            broad_query = retrieval["broad_query"]
            total_facts_scanned = retrieval["total_facts_scanned"]
            facts_selected = retrieval["facts_selected"]
        else:
            # Fallback: standard Neo4j retrieval (session init failed)
            retrieval = await retrieve_from_graph(effective_user_id, request.query)
            entity_snippets = retrieval.get("entity_snippets", {})
            history_citations = retrieval.get("history_citations", [])
            context = retrieval["context"]
            retrieval_time_ms = retrieval["retrieval_time_ms"]
            entities_found = retrieval["entities_found"]
            broad_query = retrieval.get("broad_query", False)
            total_facts_scanned = retrieval.get("total_facts_scanned", 0)
            facts_selected = retrieval.get("facts_selected", 0)

            memory_citations = [
                MemoryCitation(
                    node_id=entity, title=entity,
                    snippet=entity_snippets.get(entity, ""),
                ) for entity in entities_found[:6]
            ]
            if not memory_citations and history_citations:
                memory_citations = [
                    MemoryCitation(
                        node_id=h["node_id"], title=h["title"], snippet=h["snippet"],
                    ) for h in history_citations[:4]
                ]

        # ── Generate answer ──
        answer = await generate_answer(request.query, context)

        # ── Background: extract knowledge + sync graph (with embeddings) ──
        db = get_db()
        _driver = db._driver
        if _driver and effective_user_id in _USER_GRAPHS:
            from backend.llm_service import _chat as _llm_chat
            async def _llm_fn(sys_p: str, usr_p: str) -> str:
                return await asyncio.to_thread(_llm_chat, sys_p, usr_p)
            asyncio.create_task(
                extract_and_sync_graph(effective_user_id, request.query, _driver, _llm_fn)
            )
        else:
            # Fallback: old ingest path (no embeddings)
            async def _bg_ingest():
                try:
                    await ingest_to_graph(effective_user_id, request.query)
                except Exception as ingest_exc:
                    logger.warning("Auto-ingest failed (non-fatal): %s", ingest_exc)
            asyncio.create_task(_bg_ingest())

        return ChatResponse(
            answer=answer,
            response=answer,
            retrieval_time_ms=retrieval_time_ms,
            context_used=context,
            entities_found=entities_found,
            total_facts_scanned=total_facts_scanned,
            facts_selected=facts_selected,
            memory_citations=memory_citations,
            broad_query=broad_query,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}")


# ── Chat Stream (SSE) ─────────────────────────────────────────

@app.post(
    "/chat/stream",
    tags=["Memory"],
    summary="Chat with Streaming (SSE) — in-memory CQRS",
    description=(
        "Streams the answer token-by-token via Server-Sent Events.\n\n"
        "**Read path**: if the user's session is loaded in RAM, retrieval uses "
        "Aho-Corasick + Multi-Source BFS (< 15ms, zero Neo4j queries). "
        "Falls back to Neo4j retrieval if session is not yet warm.\n\n"
        "**Write path**: BackgroundTask runs LLM extraction and Neo4j MERGE "
        "after the stream is sent."
    ),
    responses={
        200: {"description": "SSE stream of token chunks + final metadata"},
        401: {"description": "Not authenticated"},
    },
)
async def chat_stream(
    request: ChatRequest,
    background: BackgroundTasks,
    req: Request,
    user_id: str = Depends(get_current_user),
):
    """Chat with in-memory CQRS streaming."""
    import json as _json
    effective_user_id = request.user_id or user_id
    driver = getattr(req.app.state, "neo4j_driver", None)

    # ── Lazy-init: load session into RAM if not already warm ──────────────
    if effective_user_id not in _USER_GRAPHS and driver:
        try:
            await init_user_session(effective_user_id, driver)
            logger.info("Lazy session init for /chat/stream user=%s", effective_user_id)
        except Exception as init_exc:
            logger.warning("Session init failed (non-fatal): %s", init_exc)

    # ── Read path: hybrid in-memory (preferred) vs Neo4j (fallback) ────────
    if effective_user_id in _USER_GRAPHS:
        # ── FAST PATH: Hybrid retrieval (graph + vector, all RAM) ─────────
        retrieval_meta = _hybrid_retrieve(effective_user_id, request.query)
        context = retrieval_meta["context"]

        # Fire-and-forget: extract new knowledge + sync to Neo4j + update RAM
        if driver:
            from backend.llm_service import _chat  # type: ignore[attr-defined]
            async def _llm_fn(sys_p: str, usr_p: str) -> str:
                import asyncio as _aio
                return await _aio.to_thread(_chat, sys_p, usr_p)
            background.add_task(
                extract_and_sync_graph,
                effective_user_id, request.query, driver, _llm_fn,
            )

    else:
        # ── FALLBACK PATH: standard Neo4j retrieval (init failed) ─────────
        retrieval = await retrieve_from_graph(effective_user_id, request.query)
        entity_snippets   = retrieval.get("entity_snippets", {})
        history_citations = retrieval.get("history_citations", [])
        broad_query       = retrieval.get("broad_query", False)
        context           = retrieval["context"]

        memory_citations = [
            {"node_id": e, "title": e, "snippet": entity_snippets.get(e, "")}
            for e in retrieval["entities_found"][:6]
        ]
        if not memory_citations and history_citations:
            memory_citations = [
                {"node_id": h["node_id"], "title": h["title"], "snippet": h["snippet"]}
                for h in history_citations[:4]
            ]

        retrieval_meta = {
            "retrieval_time_ms":   retrieval["retrieval_time_ms"],
            "memory_citations":    memory_citations,
            "broad_query":         broad_query,
            "entities_found":      retrieval["entities_found"],
            "total_facts_scanned": retrieval.get("total_facts_scanned", 0),
            "facts_selected":      retrieval.get("facts_selected", 0),
            "source":              "neo4j",
        }
        # Legacy background ingest
        async def _bg_ingest():
            try:
                await ingest_to_graph(effective_user_id, request.query)
            except Exception:
                pass
        asyncio.create_task(_bg_ingest())

    # ── Stream LLM tokens ────────────────────────────────────────────────────
    def _sse_generator():
        try:
            for chunk in generate_answer_stream(request.query, context):
                yield f"data: {_json.dumps({'token': chunk})}\n\n"
        except Exception as exc:
            yield f"data: {_json.dumps({'error': str(exc)})}\n\n"
        # Done sentinel — matches existing frontend parser exactly
        yield f"data: {_json.dumps({'done': True, **retrieval_meta})}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )


# ── Ingest (authenticated) ────────────────────────────────────

@app.post(
    "/ingest",
    response_model=IngestResponse,
    tags=["Memory"],
    summary="Ingest Memory",
    description="Manually ingest text into the user's knowledge graph.",
    responses={401: {"description": "Not authenticated"}},
)
async def ingest(
    request: IngestRequest,
    user_id: str = Depends(get_current_user),
):
    """Ingest text into the user's graph."""
    effective_user_id = request.user_id or user_id
    try:
        result = await ingest_to_graph(effective_user_id, request.text)
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        title = request.title.strip() or request.text[:50].rstrip(".") + "…"
        return IngestResponse(
            status="ok",
            entities_created=result["entities_created"],
            facts_created=result["facts_created"],
            id=doc_id,
            title=title,
            type=request.source_type,
            chunks=1,
            nodesCreated=result["entities_created"],
            edgesCreated=result["facts_created"],
        )
    except Exception as exc:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=f"Ingest error: {exc}")


# ── Memory Ingest (frontend-compatible alias) ─────────────────

@app.post(
    "/memory/ingest",
    response_model=IngestResponse,
    tags=["Memory"],
    summary="Ingest Document (frontend API)",
    description="Frontend-compatible route. Chunks text, extracts graph, stores in Neo4j.",
    responses={401: {"description": "Not authenticated"}},
)
async def memory_ingest(
    request: IngestRequest,
    user_id: str = Depends(get_current_user),
):
    """Frontend-compatible /memory/ingest — auto-chunks and ingests text."""
    effective_user_id = request.user_id or user_id
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Chunk large text (keep under 3000 chars per LLM call)
        text = request.text
        chunk_size = 2000
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]

        total_entities = 0
        total_facts = 0
        for chunk in chunks:
            result = await ingest_to_graph(effective_user_id, chunk)
            total_entities += result["entities_created"]
            total_facts += result["facts_created"]

        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        title = request.title.strip() or text[:50].rstrip(".") + "…"

        # Refresh in-memory CQRS cache so /chat sees the new data
        driver = getattr(app.state, "neo4j_driver", None) or getattr(get_db(), "_driver", None)
        if driver:
            try:
                await init_user_session(effective_user_id, driver)
                logger.info("Session refreshed after ingest for user=%s", effective_user_id)
            except Exception as e:
                logger.warning("Session refresh after ingest failed (non-fatal): %s", e)

        return IngestResponse(
            status="ok",
            entities_created=total_entities,
            facts_created=total_facts,
            id=doc_id,
            title=title,
            type=request.source_type,
            chunks=len(chunks),
            nodesCreated=total_entities,
            edgesCreated=total_facts,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Memory ingest failed")
        raise HTTPException(status_code=500, detail=f"Ingest error: {exc}")

@app.post(
    "/upload",
    tags=["Memory"],
    summary="Upload File to Ingest",
    description="Upload a PDF or TXT file. Text is extracted and ingested into the knowledge graph.",
    responses={401: {"description": "Not authenticated"}},
)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Extract text from uploaded PDF/TXT and ingest into graph."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "txt", "text", "md"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Use PDF, TXT, or MD files.",
        )

    content = await file.read()

    try:
        if ext == "pdf":
            import io
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="PyPDF2 not installed. Run: pip install PyPDF2",
                )
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            ).strip()
        else:
            # TXT / MD
            text = content.decode("utf-8", errors="ignore").strip()

        if not text:
            raise HTTPException(status_code=400, detail="No text content found in file.")

        # Chunk large documents (max ~3000 chars per chunk for LLM)
        chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
        total_entities = 0
        total_facts = 0

        for chunk in chunks:
            result = await ingest_to_graph(user_id, chunk)
            total_entities += result["entities_created"]
            total_facts += result["facts_created"]

        # Refresh in-memory CQRS cache so /chat sees the new data
        driver = getattr(app.state, "neo4j_driver", None) or getattr(get_db(), "_driver", None)
        if driver:
            try:
                await init_user_session(user_id, driver)
                logger.info("Session refreshed after upload for user=%s", user_id)
            except Exception as e:
                logger.warning("Session refresh after upload failed (non-fatal): %s", e)

        return {
            "status": "ok",
            "filename": filename,
            "chunks_processed": len(chunks),
            "entities_created": total_entities,
            "facts_created": total_facts,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("File upload ingest failed")
        raise HTTPException(status_code=500, detail=f"Upload error: {exc}")


# ── Knowledge Graph (authenticated) ───────────────────────────

@app.get(
    "/mindmap",
    response_model=MindmapResponse,
    tags=["Memory"],
    summary="Get Knowledge Graph",
    description="Returns the user's complete knowledge graph (nodes + edges) for visualization.",
    responses={401: {"description": "Not authenticated"}},
)
async def mindmap(
    user_id: str = Depends(get_current_user),
):
    """Return the user's graph for visualization."""
    try:
        graph = get_user_graph(user_id)
        return MindmapResponse(
            user_id=user_id,
            nodes=graph["nodes"],
            edges=graph["edges"],
        )
    except Exception as exc:
        logger.exception("Mindmap failed")
        raise HTTPException(status_code=500, detail=f"Mindmap error: {exc}")


# ── Helper: convert raw graph to React Flow format ─────────────

_NODE_TYPE_MAP = {
    "fact": "fact",
    "document": "document",
    "user": "entity",
    "category": "category",
    "technology": "entity",
    "person": "entity",
    "skill": "entity",
    "topic": "entity",
    "concept": "entity",
    "entity": "entity",
    "preference": "preference",
    "goal": "goal",
    "event": "event",
    "message": "entity",
    "document_chunk": "document",
    "resource": "document",
    "symptom": "entity",
    "medication": "entity",
    "expense": "entity",
    "destination": "entity",
    # Legacy
    "content": "entity",
    "request": "entity",
}


def _graph_to_react_flow(
    raw_nodes: list, raw_edges: list
) -> ReactFlowMindmapResponse:
    """Convert raw Neo4j graph to React Flow — hierarchical radial layout.

    Tier 0: User node at origin (0, 0)
    Tier 1: Category nodes in inner ring  (r = 300)
    Tier 2: Entity nodes clustered around their Category (r_cat + 220)
    Tier 3: Fact nodes offset below their parent entity (hidden by default)

    Cross-entity RELATED_TO edges are included as dashed links.
    """
    # ── Build category → entity map from CONTAINS edges ────────
    cat_to_entities: Dict[str, List[str]] = {}
    entity_to_facts: Dict[str, List[str]] = {}
    for edge in raw_edges:
        if edge.get("label") == "CONTAINS":
            cat_id = edge["source"]
            ent_id = edge["target"]
            cat_to_entities.setdefault(cat_id, []).append(ent_id)
        elif edge.get("label") == "HAS_FACT":
            ent_id = edge["source"]
            fact_id = edge["target"]
            entity_to_facts.setdefault(ent_id, []).append(fact_id)

    # ── Separate node tiers ──────────────────────────────────────
    user_nodes = [n for n in raw_nodes if n.get("group") == "User"]
    cat_nodes  = [n for n in raw_nodes if n.get("group") == "Category"]
    fact_nodes = [n for n in raw_nodes if n.get("group") == "Fact"]
    # Entity tier: everything except User, Category, Fact
    entity_ids = {
        n["id"] for n in raw_nodes
        if n.get("group") not in ("User", "Category", "Fact")
    }

    # ── Compute positions ────────────────────────────────────────
    positions: Dict[str, tuple] = {}

    for un in user_nodes:
        positions[un["id"]] = (0, 0)

    n_cats = len(cat_nodes)
    cat_angles: Dict[str, float] = {}
    for i, cat in enumerate(cat_nodes):
        angle = (2 * math.pi * i) / max(n_cats, 1)
        cat_angles[cat["id"]] = angle
        positions[cat["id"]] = (
            round(300 * math.cos(angle), 1),
            round(300 * math.sin(angle), 1),
        )

    # Spread entity nodes in an arc around their parent category
    for cat in cat_nodes:
        ents = [e for e in cat_to_entities.get(cat["id"], []) if e in entity_ids]
        n_ents = len(ents)
        cat_angle = cat_angles.get(cat["id"], 0)
        cat_x, cat_y = positions.get(cat["id"], (0, 0))
        spread = math.pi * 0.55  # ~100° arc
        for j, ent_id in enumerate(ents):
            if n_ents == 1:
                ent_angle = cat_angle
            else:
                ent_angle = cat_angle - spread / 2 + spread * j / (n_ents - 1)
            positions[ent_id] = (
                round(cat_x + 220 * math.cos(ent_angle), 1),
                round(cat_y + 220 * math.sin(ent_angle), 1),
            )

    # Position fact nodes below their parent entities
    for ent_id, fact_ids in entity_to_facts.items():
        ent_x, ent_y = positions.get(ent_id, (0, 0))
        for k, fact_id in enumerate(fact_ids):
            positions[fact_id] = (
                round(ent_x + (k - len(fact_ids) / 2) * 160, 1),
                round(ent_y + 150, 1),
            )

    # ── Build React Flow nodes ───────────────────────────────────
    rf_nodes: List[ReactFlowNode] = []
    rf_edges: List[ReactFlowEdge] = []

    for node in raw_nodes:
        nid = node["id"]
        group_raw = (node.get("group") or "entity").lower()
        is_hidden = bool(node.get("hidden_by_default", False))

        if group_raw == "user":
            node_type = "entity"
        elif group_raw == "category":
            node_type = "category"
        else:
            node_type = _NODE_TYPE_MAP.get(group_raw, "entity")

        pos = positions.get(nid, (0, 0))
        fact_count = node.get("facts") or 0
        rf_nodes.append(ReactFlowNode(
            id=nid,
            type=node_type,
            data=ReactFlowNodeData(
                label=node.get("label", nid),
                description=f"{fact_count} fact{'s' if fact_count != 1 else ''}" if fact_count else "",
                nodeType=node_type,
                docSource="",
                hiddenByDefault=is_hidden,
            ),
            position=ReactFlowPosition(x=pos[0], y=pos[1]),
        ))

    # ── Build React Flow edges ───────────────────────────────────
    seen_edge_ids: set = set()
    for i, edge in enumerate(raw_edges):
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if not src or not tgt:
            continue
        edge_id = f"e_{src[:10]}_{tgt[:10]}_{i}"
        if edge_id in seen_edge_ids:
            continue
        seen_edge_ids.add(edge_id)
        label = edge.get("label", "")
        rf_edges.append(ReactFlowEdge(
            id=edge_id,
            source=src,
            target=tgt,
            label=label if label not in ("HAS_CATEGORY", "CONTAINS") else "",
            animated=label == "HAS_CATEGORY",
        ))

    return ReactFlowMindmapResponse(nodes=rf_nodes, edges=rf_edges)


# ── Memory Mindmap (frontend-compatible React Flow format) ─────

@app.get(
    "/memory/mindmap",
    response_model=ReactFlowMindmapResponse,
    tags=["Memory"],
    summary="Get Knowledge Graph (React Flow)",
    description=(
        "Returns the user's knowledge graph formatted for React Flow. "
        "Nodes include type, position, and data. Accepts `user_id` as query param."
    ),
    responses={401: {"description": "Not authenticated"}},
)
async def memory_mindmap(
    user_id: str = Depends(get_current_user),
):
    """Return the user's graph in React Flow format."""
    try:
        graph = get_user_graph(user_id)
        return _graph_to_react_flow(graph["nodes"], graph["edges"])
    except Exception as exc:
        logger.exception("Memory mindmap failed")
        raise HTTPException(status_code=500, detail=f"Mindmap error: {exc}")


# ── User Profile (authenticated) ──────────────────────────────

@app.get(
    "/profile",
    response_model=UserProfileResponse,
    tags=["Learning Path Planner"],
    summary="User Knowledge Profile",
    description="Returns what the user already knows — entities, types, and fact counts.",
    responses={401: {"description": "Not authenticated"}},
)
async def profile(
    user_id: str = Depends(get_current_user),
):
    """Get the user's knowledge profile."""
    try:
        data = get_user_profile(user_id)
        return UserProfileResponse(**data)
    except Exception as exc:
        logger.exception("Profile failed")
        raise HTTPException(status_code=500, detail=f"Profile error: {exc}")


# ── Learning Roadmap (authenticated) ──────────────────────────

@app.post(
    "/roadmap",
    response_model=LearningRoadmapResponse,
    tags=["Learning Path Planner"],
    summary="Generate Learning Roadmap",
    description=(
        "Given a target skill, generates a personalized learning roadmap. "
        "Uses the user's existing knowledge graph to skip topics already known "
        "and mark prerequisites."
    ),
    responses={
        401: {"description": "Not authenticated"},
        503: {"description": "LLM provider unavailable"},
    },
)
async def roadmap(
    request: RoadmapRequest,
    user_id: str = Depends(get_current_user),
):
    """Generate a learning roadmap for a target skill."""
    try:
        # Get user's existing knowledge for context
        profile_data = get_user_profile(user_id)
        known_topics = [e["name"] for e in profile_data["entities"]]

        # Build context from profile
        context_lines = []
        for e in profile_data["entities"]:
            context_lines.append(
                f"- Knows: {e['name']} (type: {e['type']}, {e['fact_count']} facts)"
            )
        context = "\n".join(context_lines) if context_lines else "(No prior knowledge)"

        # Generate roadmap
        raw = await generate_learning_roadmap(request.target_skill, context)

        # Parse steps
        steps = []
        for s in raw.get("steps", []):
            steps.append(RoadmapStep(
                order=s.get("order", 0),
                topic=s.get("topic", ""),
                description=s.get("description", ""),
                already_known=s.get("already_known", False),
                prerequisites=s.get("prerequisites", []),
                resources=s.get("resources", []),
            ))

        return LearningRoadmapResponse(
            target_skill=request.target_skill,
            steps=steps,
            known_topics=known_topics,
            estimated_time=raw.get("estimated_time", ""),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Roadmap generation failed")
        raise HTTPException(status_code=500, detail=f"Roadmap error: {exc}")


# ── API Root ───────────────────────────────────────────────────


@app.get("/", tags=["System"], summary="API Root", include_in_schema=True)
async def root():
    """API information. Frontend is served separately by Vite (port 5173)."""
    return {
        "name": "GraphMind API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "note": "Frontend runs on http://localhost:5173 (Vite dev server)",
    }

