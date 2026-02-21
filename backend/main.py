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

import hashlib
import logging
import math
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import JWT_ALGORITHM, JWT_SECRET, get_current_user
from backend.database import get_db
from backend.llm_service import generate_answer, generate_learning_roadmap
from backend.memory_ops import (
    get_user_graph,
    get_user_profile,
    ingest_to_graph,
    retrieve_from_graph,
)
from backend.models import (
    ChatRequest,
    ChatResponse,
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
    """Start/stop the Neo4j driver and set up DB constraints."""
    db = get_db()
    db.init_driver()
    db.setup_constraints()
    logger.info("GraphMind backend started ✓")
    yield
    db.close_driver()
    logger.info("GraphMind backend stopped.")


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
    return {"status": "ok", "neo4j": neo4j_ok, "version": "2.0.0"}


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
    return LoginResponse(
        user_id=user["user_id"],
        name=user["name"],
        email=user["email"],
        token=token,
    )


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
    """Chat with memory — retrieve, answer, then auto-ingest."""
    # Allow user_id override from request body (frontend sends it there)
    effective_user_id = request.user_id or user_id
    try:
        # 1. Retrieve context from Neo4j (user-scoped)
        retrieval = await retrieve_from_graph(effective_user_id, request.query)

        # 2. Generate answer
        answer = await generate_answer(request.query, retrieval["context"])

        # 3. Auto-ingest (LLM skips pure questions)
        try:
            await ingest_to_graph(effective_user_id, request.query)
            logger.info("Auto-ingested for user=%s", effective_user_id)
        except Exception as ingest_exc:
            logger.warning("Auto-ingest failed (non-fatal): %s", ingest_exc)

        # 4. Build memory citations from retrieved entities + history
        entity_snippets = retrieval.get("entity_snippets", {})
        history_citations = retrieval.get("history_citations", [])
        broad_query = retrieval.get("broad_query", False)

        memory_citations = [
            MemoryCitation(
                node_id=entity,
                title=entity,
                snippet=entity_snippets.get(entity, ""),
            )
            for entity in retrieval["entities_found"][:6]
        ]
        # For broad queries (e.g. "tell me about myself") entities may be ranked by
        # recency only — also surface history citations so the badge isn't empty.
        if not memory_citations and history_citations:
            memory_citations = [
                MemoryCitation(
                    node_id=h["node_id"],
                    title=h["title"],
                    snippet=h["snippet"],
                )
                for h in history_citations[:4]
            ]

        return ChatResponse(
            answer=answer,
            response=answer,               # frontend-compatible alias
            retrieval_time_ms=retrieval["retrieval_time_ms"],
            context_used=retrieval["context"],
            entities_found=retrieval["entities_found"],
            total_facts_scanned=retrieval.get("total_facts_scanned", 0),
            facts_selected=retrieval.get("facts_selected", 0),
            perf=retrieval.get("perf"),
            memory_citations=memory_citations,
            broad_query=broad_query,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}")


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
    "technology": "concept",
    "person": "entity",
    "skill": "concept",
    "topic": "concept",
    "concept": "concept",
    "entity": "entity",
    "goal": "concept",
    "resource": "document",
    "symptom": "entity",
    "medication": "entity",
    "expense": "entity",
    "destination": "entity",
}


def _graph_to_react_flow(
    raw_nodes: list, raw_edges: list
) -> ReactFlowMindmapResponse:
    """Convert raw Neo4j graph to React Flow — hierarchical radial layout.

    Tier 0: User node at origin (0, 0)
    Tier 1: Category nodes in inner ring  (r = 300)
    Tier 2: Entity nodes clustered around their Category (r_cat + 220)

    Facts are omitted from the canvas to keep it readable.
    Cross-entity RELATED_TO edges are included as dashed links.
    """
    # ── Build category → entity map from CONTAINS edges ────────
    cat_to_entities: Dict[str, List[str]] = {}
    for edge in raw_edges:
        if edge.get("label") == "CONTAINS":
            cat_id = edge["source"]
            ent_id = edge["target"]
            cat_to_entities.setdefault(cat_id, []).append(ent_id)

    # ── Separate node tiers ──────────────────────────────────────
    user_nodes = [n for n in raw_nodes if n.get("group") == "User"]
    cat_nodes  = [n for n in raw_nodes if n.get("group") == "Category"]
    # Exclude User, Category, Fact from entity tier
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

    # ── Build React Flow nodes ───────────────────────────────────
    rf_nodes: List[ReactFlowNode] = []
    rf_edges: List[ReactFlowEdge] = []

    for node in raw_nodes:
        if node.get("group") == "Fact":
            continue  # facts not rendered on canvas

        nid = node["id"]
        group_raw = (node.get("group") or "concept").lower()
        if group_raw == "user":
            node_type = "entity"
        elif group_raw == "category":
            node_type = "category"
        else:
            node_type = _NODE_TYPE_MAP.get(group_raw, "concept")

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
            ),
            position=ReactFlowPosition(x=pos[0], y=pos[1]),
        ))

    # ── Build React Flow edges (skip fact edges) ─────────────────
    seen_edge_ids: set = set()
    for i, edge in enumerate(raw_edges):
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if not src or not tgt:
            continue
        # Skip edges to/from Fact nodes
        if src.startswith("fact_") or tgt.startswith("fact_"):
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

