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


class ChatRequest(BaseModel):
    """Payload to ask a question using memory context."""
    query: str = Field(
        ..., min_length=1,
        description="The user's current question.",
    )


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


class IngestResponse(BaseModel):
    """Acknowledgement from /ingest endpoint."""
    status: str = Field(default="ok")
    entities_created: int = Field(default=0)
    facts_created: int = Field(default=0)
    message: str = Field(default="Memory ingested successfully.")


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


# ── Chat Session Models ─────────────────────────────────────────


class ChatMessage(BaseModel):
    """A single message in a chat session."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text.")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp.")


class ChatSessionSummary(BaseModel):
    """Summary of a chat session (for listing)."""
    session_id: str = Field(..., description="Unique session identifier.")
    title: str = Field(default="New Chat", description="Session title (first user message).")
    message_count: int = Field(default=0)
    created_at: str = Field(default="", description="ISO timestamp of creation.")
    updated_at: str = Field(default="", description="ISO timestamp of last message.")


class ChatSessionDetail(BaseModel):
    """Full chat session with all messages."""
    session_id: str
    title: str = Field(default="New Chat")
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(default="")
    updated_at: str = Field(default="")


class ChatSessionListResponse(BaseModel):
    """Response from /chat-sessions endpoint."""
    sessions: List[ChatSessionSummary] = Field(default_factory=list)
