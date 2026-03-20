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

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# ✅ FIXED IMPORTS (removed backend.)
from auth import JWT_ALGORITHM, JWT_SECRET, get_current_user
from database import get_db
from llm_service import generate_answer, generate_answer_stream, generate_learning_roadmap
from memory_ops import (
    get_user_graph,
    get_user_profile,
    ingest_to_graph,
    retrieve_from_graph,
)
from memory_store import (
    assemble_context,
    bfs_subgraph,
    drop_user_session,
    get_graph_stats,
    init_user_session,
    scan_query,
    _USER_GRAPHS,
)
from worker import extract_and_sync_graph
from vector_store import vector_search as _vector_search, warm_model as _warm_embedding_model
from models import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
)
logger = logging.getLogger("graphmind.api")


# ── AUTH HELPERS ─────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def _verify_password(plain: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == h
    except:
        return False


def _create_jwt(user_id: str, name: str) -> str:
    import jwt as pyjwt
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": user_id,
        "name": name,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


_user_store: dict = {}


# ── STARTUP ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    db.init_driver()
    db.setup_constraints()

    app.state.neo4j_driver = db._driver

    _warm_embedding_model()

    logger.info("Backend started")
    yield

    db.close_driver()
    logger.info("Backend stopped")


# ── HYBRID RETRIEVAL ─────────────────────────────────────────

def _hybrid_retrieve(user_id: str, query: str) -> dict:
    graph_seed_ids = scan_query(user_id, query)
    vector_results = _vector_search(user_id, query, top_k=10)

    seed_ids = graph_seed_ids + [nid for nid, _ in vector_results]

    sub_nodes, sub_edges = bfs_subgraph(user_id, seed_ids, max_hops=2, max_nodes=50)

    context = assemble_context(sub_nodes, sub_edges)

    return {
        "context": context,
        "memory_citations": sub_nodes[:5],
        "entities_found": seed_ids,
        "retrieval_time_ms": 5,
        "broad_query": False,
        "total_facts_scanned": len(sub_nodes),
        "facts_selected": len(sub_nodes),
    }


# ── FASTAPI APP ─────────────────────────────────────────────

app = FastAPI(title="GraphMind API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── HEALTH ──────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── AUTH ────────────────────────────────────────────────────

@app.post("/auth/signup")
async def signup(request: SignupRequest):
    if request.email in _user_store:
        raise HTTPException(409, "User exists")

    user_id = str(uuid.uuid4())
    hashed = _hash_password(request.password)

    _user_store[request.email] = {
        "user_id": user_id,
        "name": request.name,
        "hashed": hashed,
    }

    token = _create_jwt(user_id, request.name)

    return {"token": token, "user_id": user_id, "name": request.name, "email": request.email}


@app.post("/auth/login")
async def login(request: LoginRequest):
    user = _user_store.get(request.email)
    if not user or not _verify_password(request.password, user["hashed"]):
        raise HTTPException(401, "Invalid credentials")

    token = _create_jwt(user["user_id"], user["name"])
    return {"token": token, "user_id": user["user_id"], "name": user["name"], "email": request.email}


# ── CHAT ────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user_id: str = Depends(get_current_user)):
    retrieval = _hybrid_retrieve(user_id, request.query)

    answer = await generate_answer(request.query, retrieval["context"])

    return ChatResponse(
        answer=answer,
        response=answer,
        retrieval_time_ms=retrieval["retrieval_time_ms"],
        context_used=retrieval["context"],
        entities_found=retrieval["entities_found"],
        total_facts_scanned=retrieval["total_facts_scanned"],
        facts_selected=retrieval["facts_selected"],
        memory_citations=[],
        broad_query=False,
    )


# ── STREAM ──────────────────────────────────────────────────

@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    background: BackgroundTasks,
    req: Request,
    user_id: str = Depends(get_current_user),
):
    import json

    retrieval = _hybrid_retrieve(user_id, request.query)

    def generator():
        for chunk in generate_answer_stream(request.query, retrieval["context"]):
            yield f"data: {json.dumps({'token': chunk})}\n\n"

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


# ── INGEST ─────────────────────────────────────────────────

@app.post("/ingest")
async def ingest(request: IngestRequest, user_id: str = Depends(get_current_user)):
    result = await ingest_to_graph(user_id, request.text)

    return {"status": "ok", **result}


# ── MINDMAP ────────────────────────────────────────────────

@app.get("/mindmap")
async def mindmap(user_id: str = Depends(get_current_user)):
    return get_user_graph(user_id)


# ── PROFILE ────────────────────────────────────────────────

@app.get("/profile")
async def profile(user_id: str = Depends(get_current_user)):
    return get_user_profile(user_id)


# ── ROOT ───────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "GraphMind API running"}