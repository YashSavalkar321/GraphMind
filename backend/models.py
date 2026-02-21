"""
GraphMind — Pydantic Data Models
=================================
All request/response schemas for the GraphMind API.
Uses Pydantic v2 (model_config style).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


# ── Request Models ──────────────────────────────────────────────


class IngestRequest(BaseModel):
    """Payload to write a new memory into the graph."""
    text: str = Field(
        ..., min_length=1,
        description="Raw user message to extract entities/facts from.",
    )
    user_id: Optional[str] = Field(default=None, description="User ID (can also come from JWT).")
    source_type: str = Field(default="text", description="Source type: text, file, url.")
    title: str = Field(default="", description="Optional document title.")


class ChatRequest(BaseModel):
    """Payload to ask a question using memory context."""
    query: str = Field(
        ..., min_length=1,
        description="The user's current question.",
    )
    user_id: Optional[str] = Field(default=None, description="User ID (can also come from JWT).")


class RoadmapRequest(BaseModel):
    """Payload to generate a learning roadmap."""
    target_skill: str = Field(
        ..., min_length=1,
        description="The skill/topic the user wants to learn.",
    )


# ── Internal DTOs ───────────────────────────────────────────────


class MemoryEntity(BaseModel):
    """A single entity extracted by the LLM from user text."""
    name: str = Field(..., description="Name of the entity.")
    type: str = Field(..., description="Category (Technology, Person, Skill, etc.).")


class MemoryRelationship(BaseModel):
    """A relationship extracted between two entities."""
    source: str
    relation: str
    target: str


class MemoryFact(BaseModel):
    """A distinct fact extracted from the user's message."""
    content: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    entity_name: Optional[str] = None


class ExtractionResult(BaseModel):
    """Full output of the LLM extraction step."""
    entities: List[MemoryEntity] = Field(default_factory=list)
    relationships: List[MemoryRelationship] = Field(default_factory=list)
    facts: List[MemoryFact] = Field(default_factory=list)

# ── Memory Citation ────────────────────────────────────────────


class MemoryCitation(BaseModel):
    """A memory node citation returned alongside chat answers."""
    node_id: str = Field(..., description="Graph node identifier.")
    title: str = Field(..., description="Display name of the cited memory node.")
    snippet: str = Field(default="", description="Short excerpt from the node.")

# ── Response Models ─────────────────────────────────────────────


class ChatResponse(BaseModel):
    """Response from /chat endpoint."""
    answer: str = Field(..., description="The LLM-generated answer.")
    retrieval_time_ms: float = Field(
        ..., description="Total retrieval time in milliseconds.",
    )
    context_used: str = Field(default="", description="Raw memory context fed to LLM.")
    entities_found: List[str] = Field(
        default_factory=list, description="Matched entity names.",
    )
    total_facts_scanned: int = Field(default=0, description="Total facts evaluated.")
    facts_selected: int = Field(default=0, description="Top-N facts after relevance filter.")
    perf: Optional[dict] = Field(default=None, description="Performance breakdown (ms).")
    memory_citations: List[MemoryCitation] = Field(
        default_factory=list, description="Graph nodes cited in the answer.",
    )
    # Frontend-compatible alias for `answer`
    response: str = Field(default="", description="Alias for `answer` (frontend contract).")
    # True when the query had no specific keywords (broad question like "tell me about myself")
    broad_query: bool = Field(default=False, description="True for general/broad queries answered from history.")


class IngestResponse(BaseModel):
    """Acknowledgement from /ingest endpoint."""
    status: str = Field(default="ok")
    entities_created: int = Field(default=0)
    facts_created: int = Field(default=0)
    message: str = Field(default="Memory ingested successfully.")
    # Frontend-compatible fields (sdBackend contract)
    id: str = Field(default="")
    title: str = Field(default="")
    type: str = Field(default="text")
    chunks: int = Field(default=1)
    nodesCreated: int = Field(default=0)
    edgesCreated: int = Field(default=0)


class UserProfileResponse(BaseModel):
    """What the user already knows — returned by /profile."""
    user_id: str
    entities: List[dict] = Field(
        default_factory=list,
        description="Entities the user knows, with types and fact counts.",
    )
    total_facts: int = Field(default=0)
    total_entities: int = Field(default=0)
    total_interactions: int = Field(default=0, description="Total conversation memories stored.")


class RoadmapStep(BaseModel):
    """A single step in a learning roadmap."""
    order: int
    topic: str
    description: str
    already_known: bool = False
    prerequisites: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)


class LearningRoadmapResponse(BaseModel):
    """Response from /roadmap endpoint."""
    target_skill: str
    steps: List[RoadmapStep] = Field(default_factory=list)
    known_topics: List[str] = Field(
        default_factory=list,
        description="Topics the user already knows (from their graph).",
    )
    estimated_time: str = Field(default="", description="Estimated completion time.")


# ── Mindmap / Graph Visualization Models ────────────────────────


class MindmapNode(BaseModel):
    """A single node for the streamlit-agraph visualizer."""
    id: str = Field(..., description="Unique node identifier.")
    label: str = Field(..., description="Display label.")
    group: Optional[str] = Field(
        default="default",
        description="Grouping key (maps to node color).",
    )

    @model_validator(mode="before")
    @classmethod
    def _fill_none_group(cls, values):
        if isinstance(values, dict) and not values.get("group"):
            values["group"] = "default"
        return values


class MindmapEdge(BaseModel):
    """A single edge for the streamlit-agraph visualizer."""
    source: str = Field(..., description="Source node id.")
    target: str = Field(..., description="Target node id.")
    label: str = Field(default="", description="Relationship label.")


class MindmapResponse(BaseModel):
    """Full graph visualization payload for a user."""
    user_id: str
    nodes: List[MindmapNode] = Field(default_factory=list)
    edges: List[MindmapEdge] = Field(default_factory=list)


# ── Auth Models ──────────────────────────────────────────────────


class SignupRequest(BaseModel):
    """Payload for user signup."""
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class SignupResponse(BaseModel):
    """Response from /auth/signup."""
    user_id: str
    name: str
    email: str
    token: str


class LoginRequest(BaseModel):
    """Payload for user login."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Response from /auth/login."""
    user_id: str
    name: str
    email: str
    token: str


# ── React Flow / Mindmap Models ──────────────────────────────────


class ReactFlowNodeData(BaseModel):
    """Data payload for a React Flow node."""
    label: str
    description: str = ""
    nodeType: str = "concept"
    docSource: str = ""


class ReactFlowPosition(BaseModel):
    """X/Y position for a React Flow node."""
    x: float
    y: float


class ReactFlowNode(BaseModel):
    """A single React Flow node (for /memory/mindmap)."""
    id: str
    type: str = "concept"
    data: ReactFlowNodeData
    position: ReactFlowPosition


class ReactFlowEdge(BaseModel):
    """A single React Flow edge (for /memory/mindmap)."""
    id: str
    source: str
    target: str
    label: str = ""
    animated: bool = False
    style: Optional[dict] = None


class ReactFlowMindmapResponse(BaseModel):
    """React Flow graph payload returned by GET /memory/mindmap."""
    nodes: List[ReactFlowNode] = Field(default_factory=list)
    edges: List[ReactFlowEdge] = Field(default_factory=list)


# ── Chat Session Persistence Models ─────────────────────────────


class ChatMessagePayload(BaseModel):
    """A single chat message in a persisted session."""
    id: str
    role: str
    content: str
    timestamp: str
    retrieval_time_ms: Optional[float] = None
    memory_citations: Optional[List[dict]] = None
    broad_query: Optional[bool] = None


class SaveChatRequest(BaseModel):
    """Payload to save/update a chat session."""
    chat_id: str = Field(..., description="Unique chat session ID.")
    title: str = Field(default="New Chat", description="Chat title.")
    pinned: bool = Field(default=False)
    messages: List[ChatMessagePayload] = Field(default_factory=list)
    createdAt: str = Field(default="", description="ISO timestamp.")
    updatedAt: str = Field(default="", description="ISO timestamp.")


class ChatSessionResponse(BaseModel):
    """A single chat session returned by GET /chats."""
    chat_id: str
    title: str
    pinned: bool = False
    messages: List[dict] = Field(default_factory=list)
    createdAt: str = ""
    updatedAt: str = ""
