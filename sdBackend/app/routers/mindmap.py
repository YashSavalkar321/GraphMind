"""
GraphMind — GET /memory/mindmap
Returns all nodes & edges for a user, formatted for the React Flow frontend.
"""

import logging
import math
from typing import List

from fastapi import APIRouter, Query

from app.models import (
    MindmapResponse,
    MindmapNode,
    MindmapEdge,
    NodeData,
    NodePosition,
)
from app.services.neo4j_client import neo4j_client, NODE_COLORS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

# ── Edge colors by relationship type ──
EDGE_COLORS = {
    "USES": "#6366f1",
    "RELATES_TO": "#8b5cf6",
    "INCLUDES": "#0ea5e9",
    "CONTRADICTS": "#ef4444",
    "CAUSES": "#ef4444",
    "ENABLES": "#10b981",
    "REQUIRES": "#f59e0b",
    "IMPLEMENTS": "#0ea5e9",
}


@router.get("/mindmap", response_model=MindmapResponse)
async def get_mindmap(user_id: str = Query(..., description="User ID")):
    """
    Fetch all nodes & edges for a user from Neo4j.
    Auto-generates layout positions using a force-directed-like algorithm.
    """
    raw_nodes = await neo4j_client.get_all_nodes(user_id)
    raw_edges = await neo4j_client.get_all_edges(user_id)

    # ── Auto-layout positions ──
    positions = _compute_layout(raw_nodes, raw_edges)

    # ── Format nodes for React Flow ──
    nodes: List[MindmapNode] = []
    for n in raw_nodes:
        node_type = (n.get("label_type") or "Concept").lower()
        if node_type not in ("concept", "entity", "document", "fact"):
            node_type = "concept"

        node_id = n["id"]
        pos = positions.get(node_id, {"x": 0, "y": 0})

        nodes.append(
            MindmapNode(
                id=node_id,
                type=node_type,
                data=NodeData(
                    label=n.get("name", "?"),
                    description=n.get("description", ""),
                    nodeType=node_type,
                    docSource=n.get("source", ""),
                ),
                position=NodePosition(x=pos["x"], y=pos["y"]),
            )
        )

    # ── Format edges for React Flow ──
    edges: List[MindmapEdge] = []
    valid_node_ids = {n.id for n in nodes}
    for e in raw_edges:
        if e["source"] not in valid_node_ids or e["target"] not in valid_node_ids:
            continue
        rel = e.get("rel_type", "RELATES_TO")
        color = EDGE_COLORS.get(rel, "#6366f1")
        edges.append(
            MindmapEdge(
                id=e.get("id", f"e_{e['source']}_{e['target']}"),
                source=e["source"],
                target=e["target"],
                label=rel.lower().replace("_", " "),
                animated=rel in ("USES", "ENABLES", "INCLUDES"),
                style={"stroke": color},
            )
        )

    logger.info("Mindmap: %d nodes, %d edges for user %s", len(nodes), len(edges), user_id)
    return MindmapResponse(nodes=nodes, edges=edges)


def _compute_layout(
    nodes: list, edges: list, width: float = 1200, height: float = 800
) -> dict:
    """
    Simple radial/grid layout when there's no position data in Neo4j.
    Groups nodes by source document, placing each group in a cluster.
    """
    if not nodes:
        return {}

    # Group nodes by source
    groups: dict = {}
    for n in nodes:
        src = n.get("source", "default")
        groups.setdefault(src, []).append(n["id"])

    positions = {}
    num_groups = max(len(groups), 1)
    group_spacing = width / (num_groups + 1)

    for gi, (src, node_ids) in enumerate(groups.items()):
        cx = group_spacing * (gi + 1)  # center X for this group
        cy = height / 2  # center Y
        n_nodes = len(node_ids)

        if n_nodes == 1:
            positions[node_ids[0]] = {"x": cx, "y": cy}
        else:
            # Arrange in a circle around the group center
            radius = min(150, 60 * n_nodes)
            for ni, nid in enumerate(node_ids):
                angle = (2 * math.pi * ni) / n_nodes - math.pi / 2
                positions[nid] = {
                    "x": round(cx + radius * math.cos(angle)),
                    "y": round(cy + radius * math.sin(angle)),
                }

    return positions
