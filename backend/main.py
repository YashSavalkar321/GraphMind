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

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.auth import get_current_user
from backend.database import get_db
from backend.llm_service import generate_answer, generate_learning_roadmap
from backend.memory_ops import (
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    get_user_graph,
    get_user_profile,
    ingest_to_graph,
    list_chat_sessions,
    retrieve_from_graph,
    save_chat_message,
)
from backend.models import (
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionSummary,
    IngestRequest,
    IngestResponse,
    LearningRoadmapResponse,
    MindmapResponse,
    RoadmapRequest,
    RoadmapStep,
    UserProfileResponse,
)

# ── Logging ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
)
logger = logging.getLogger("graphmind.api")


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
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """Chat with memory — retrieve, answer, then auto-ingest in background."""
    try:
        # 1. Retrieve context from Neo4j (user-scoped)
        retrieval = await retrieve_from_graph(user_id, request.query)

        # 2. Generate answer
        answer = await generate_answer(request.query, retrieval["context"])

        # 3. Auto-ingest in background (non-blocking, user gets answer immediately)
        async def _bg_ingest():
            try:
                await ingest_to_graph(user_id, request.query)
                logger.info("Auto-ingested for user=%s", user_id)
            except Exception as ingest_exc:
                logger.warning("Auto-ingest failed (non-fatal): %s", ingest_exc)

        background_tasks.add_task(_bg_ingest)

        return ChatResponse(
            answer=answer,
            retrieval_time_ms=retrieval["retrieval_time_ms"],
            context_used=retrieval["context"],
            entities_found=retrieval["entities_found"],
            total_facts_scanned=retrieval.get("total_facts_scanned", 0),
            facts_selected=retrieval.get("facts_selected", 0),
            perf=retrieval.get("perf"),
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
    try:
        result = await ingest_to_graph(user_id, request.text)
        return IngestResponse(
            status="ok",
            entities_created=result["entities_created"],
            facts_created=result["facts_created"],
        )
    except Exception as exc:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=f"Ingest error: {exc}")


# ── File Upload (authenticated) ───────────────────────────────

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


# ── Chat Sessions (authenticated) ─────────────────────────────

@app.post(
    "/chat-sessions",
    response_model=ChatSessionSummary,
    tags=["Chat Sessions"],
    summary="Create Chat Session",
    description="Create a new chat session for the user.",
    responses={401: {"description": "Not authenticated"}},
)
async def create_session(
    user_id: str = Depends(get_current_user),
):
    """Create a new empty chat session."""
    try:
        import uuid
        session_id = str(uuid.uuid4())
        result = create_chat_session(user_id, session_id)
        return ChatSessionSummary(
            session_id=result["session_id"],
            title=result["title"],
            message_count=0,
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )
    except Exception as exc:
        logger.exception("Create session failed")
        raise HTTPException(status_code=500, detail=f"Session error: {exc}")


@app.get(
    "/chat-sessions",
    response_model=ChatSessionListResponse,
    tags=["Chat Sessions"],
    summary="List Chat Sessions",
    description="List all chat sessions for the current user, most recent first.",
    responses={401: {"description": "Not authenticated"}},
)
async def list_sessions(
    user_id: str = Depends(get_current_user),
):
    """List all chat sessions."""
    try:
        sessions = list_chat_sessions(user_id)
        return ChatSessionListResponse(
            sessions=[ChatSessionSummary(**s) for s in sessions]
        )
    except Exception as exc:
        logger.exception("List sessions failed")
        raise HTTPException(status_code=500, detail=f"Session error: {exc}")


@app.get(
    "/chat-sessions/{session_id}",
    response_model=ChatSessionDetail,
    tags=["Chat Sessions"],
    summary="Get Chat Session",
    description="Load all messages for a specific chat session.",
    responses={401: {"description": "Not authenticated"}},
)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    """Load a chat session with all messages."""
    try:
        data = get_chat_session(user_id, session_id)
        return ChatSessionDetail(**data)
    except Exception as exc:
        logger.exception("Get session failed")
        raise HTTPException(status_code=500, detail=f"Session error: {exc}")


@app.delete(
    "/chat-sessions/{session_id}",
    tags=["Chat Sessions"],
    summary="Delete Chat Session",
    description="Delete a chat session and all its messages.",
    responses={401: {"description": "Not authenticated"}},
)
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a chat session."""
    try:
        delete_chat_session(user_id, session_id)
        return {"status": "ok", "message": "Session deleted."}
    except Exception as exc:
        logger.exception("Delete session failed")
        raise HTTPException(status_code=500, detail=f"Delete error: {exc}")


@app.post(
    "/chat-sessions/{session_id}/messages",
    tags=["Chat Sessions"],
    summary="Save Chat Message",
    description="Save a message to a chat session.",
    responses={401: {"description": "Not authenticated"}},
)
async def save_message(
    session_id: str,
    message: dict,
    user_id: str = Depends(get_current_user),
):
    """Save a message to a session."""
    try:
        role = message.get("role", "user")
        content = message.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Message content is required.")
        save_chat_message(user_id, session_id, role, content)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Save message failed")
        raise HTTPException(status_code=500, detail=f"Save error: {exc}")


# ── Frontend Serving ───────────────────────────────────────────

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend SPA."""
    html = _FRONTEND_DIR / "index.html"
    if html.exists():
        return FileResponse(html, media_type="text/html")
    return {"message": "Frontend not found. Place index.html in frontend/"}

