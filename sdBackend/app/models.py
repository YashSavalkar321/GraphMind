"""
GraphMind — Pydantic request / response models.
Matches the frontend API contract exactly.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional


# ═══════════════════════════════════════════════
#  Auth
# ═══════════════════════════════════════════════
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class SignupResponse(BaseModel):
    user_id: str
    name: str
    email: str
    token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user_id: str
    name: str
    email: str
    token: str


# ═══════════════════════════════════════════════
#  POST /memory/ingest
# ═══════════════════════════════════════════════
class IngestRequest(BaseModel):
    user_id: str
    text: str
    source_type: str = "text"
    title: str = ""  # optional; extracted from text if missing


class IngestResponse(BaseModel):
    id: str
    title: str
    type: str
    chunks: int
    nodesCreated: int
    edgesCreated: int


# ═══════════════════════════════════════════════
#  GET /memory/mindmap
# ═══════════════════════════════════════════════
class NodePosition(BaseModel):
    x: float
    y: float


class NodeData(BaseModel):
    label: str
    description: Optional[str] = ""
    nodeType: str  # concept | entity | document | fact
    docSource: Optional[str] = ""


class MindmapNode(BaseModel):
    id: str
    type: str  # matches nodeType — used by React Flow to select the custom component
    data: NodeData
    position: NodePosition


class MindmapEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""
    animated: Optional[bool] = False
    style: Optional[dict] = None


class MindmapResponse(BaseModel):
    nodes: List[MindmapNode]
    edges: List[MindmapEdge]


# ═══════════════════════════════════════════════
#  POST /chat
# ═══════════════════════════════════════════════
class ChatRequest(BaseModel):
    user_id: str
    query: str


class MemoryCitation(BaseModel):
    node_id: str
    title: str
    snippet: str = ""


class ChatResponse(BaseModel):
    response: str
    retrieval_time_ms: float
    memory_citations: List[MemoryCitation]


# ═══════════════════════════════════════════════
#  Internal: LLM extraction output
# ═══════════════════════════════════════════════
class ExtractedNode(BaseModel):
    name: str
    node_type: str = "concept"  # concept | entity | document | fact
    description: str = ""


class ExtractedEdge(BaseModel):
    source: str  # node name
    target: str  # node name
    label: str = "relates_to"


class ExtractionResult(BaseModel):
    nodes: List[ExtractedNode]
    edges: List[ExtractedEdge]
