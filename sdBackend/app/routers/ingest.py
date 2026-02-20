"""
GraphMind — POST /memory/ingest
Ingests text: chunks it, extracts knowledge graph via LLM,
stores nodes/edges in Neo4j, and embeds chunks into Qdrant.
"""

import logging
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException

from app.models import IngestRequest, IngestResponse
from app.services.chunking import chunk_text
from app.services.extraction import extract_graph
from app.services.embeddings import embed_texts
from app.services.neo4j_client import neo4j_client
from app.services.vector_client import vector_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest):
    """
    Full ingestion pipeline:
    1. Chunk the text
    2. Extract knowledge graph (LLM)
    3. Store nodes & edges in Neo4j
    4. Embed chunks & store in Qdrant
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    title = req.title.strip() or req.text[:50].strip().rstrip(".") + "…"

    # ── Step 1: Chunk text ──
    chunks = chunk_text(req.text, max_chunk_size=500, overlap=50)
    logger.info("Chunked into %d pieces", len(chunks))

    # ── Step 2: Extract knowledge graph via LLM ──
    extraction = await extract_graph(req.text)
    logger.info(
        "Extracted %d nodes, %d edges", len(extraction.nodes), len(extraction.edges)
    )

    # ── Step 3: Store nodes in Neo4j ──
    # Map node name → node id for edge creation
    name_to_id: Dict[str, str] = {}
    nodes_created = 0

    for node in extraction.nodes:
        # Check if node already exists for this user
        existing = await neo4j_client.find_node_by_name(req.user_id, node.name)
        if existing:
            name_to_id[node.name] = existing["id"]
            logger.debug("Node '%s' already exists as %s", node.name, existing["id"])
        else:
            node_id = await neo4j_client.create_node(
                user_id=req.user_id,
                name=node.name,
                node_type=node.node_type,
                description=node.description,
                source=doc_id,
            )
            name_to_id[node.name] = node_id
            nodes_created += 1
            logger.debug("Created node '%s' → %s", node.name, node_id)

    # ── Step 4: Store edges in Neo4j ──
    edges_created = 0
    for edge in extraction.edges:
        source_id = name_to_id.get(edge.source)
        target_id = name_to_id.get(edge.target)
        if source_id and target_id:
            rel_type = edge.label.upper().replace(" ", "_")
            edge_id = await neo4j_client.create_edge(
                user_id=req.user_id,
                source_id=source_id,
                target_id=target_id,
                rel_type=rel_type,
            )
            if edge_id:
                edges_created += 1
                logger.debug(
                    "Created edge %s -[%s]-> %s", source_id, rel_type, target_id
                )

    # ── Step 5: Embed & store chunks in Qdrant ──
    chunk_texts = [c for c in chunks]
    vectors = embed_texts(chunk_texts)

    # Assign each chunk a memory_id (link to the most relevant node)
    chunk_dicts = []
    node_ids = list(name_to_id.values())
    for i, chunk in enumerate(chunk_texts):
        chunk_dicts.append({
            "chunk_text": chunk,
            "memory_id": node_ids[i % len(node_ids)] if node_ids else doc_id,
            "doc_source": doc_id,
            "title": title,
        })

    vector_client.upsert_chunks(
        user_id=req.user_id,
        chunks=chunk_dicts,
        vectors=vectors,
    )
    logger.info("Stored %d vectors in Qdrant", len(vectors))

    return IngestResponse(
        id=doc_id,
        title=title,
        type=req.source_type,
        chunks=len(chunks),
        nodesCreated=nodes_created,
        edgesCreated=edges_created,
    )
