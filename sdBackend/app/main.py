"""
GraphMind — FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ingest, chat, mindmap, auth
from app.services.neo4j_client import neo4j_client
from app.services.vector_client import vector_client
from app.services.redis_client import redis_client
from app.services.embeddings import get_model

# ── Logging ──
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan: startup / shutdown ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 GraphMind starting up…")

    # Connect to databases (graceful — don't crash if a service is down)
    try:
        await neo4j_client.connect()
    except Exception as e:
        logger.error("⚠️  Neo4j unavailable: %s — graph features will fail", e)

    try:
        await vector_client.connect()
    except Exception as e:
        logger.error("⚠️  Qdrant unavailable: %s — vector search will fail", e)

    # Connect to Redis
    try:
        await redis_client.connect()
    except Exception as e:
        logger.error("⚠️  Redis unavailable: %s — caching will be disabled", e)

    # Pre-warm embedding model
    logger.info("Loading embedding model (first-time download may take a moment)…")
    try:
        get_model()
    except Exception as e:
        logger.error("⚠️  Embedding model failed to load: %s", e)
    logger.info("✅ Startup complete")

    yield

    # Shutdown
    logger.info("Shutting down…")
    await neo4j_client.close()
    await vector_client.close()
    await redis_client.close()


# ── App ──
app = FastAPI(
    title="GraphMind API",
    description="Memory-grounded AI with Knowledge Graph + Vector retrieval",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(mindmap.router)


# ── Health check ──
@app.get("/health")
async def health():
    return {"status": "ok", "service": "graphmind-api"}
