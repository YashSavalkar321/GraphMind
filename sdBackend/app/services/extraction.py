"""
GraphMind — Knowledge Graph extraction pipeline.
Uses the LLM with a strict system prompt to extract nodes & edges as JSON.
NO LangChain, NO LlamaIndex — just engineered prompts.
"""

import logging
from typing import List, Tuple

from app.models import ExtractedNode, ExtractedEdge, ExtractionResult
from app.services.llm_client import llm_generate, parse_json_from_llm

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  System prompt for knowledge-graph extraction
# ═══════════════════════════════════════════════════════════

EXTRACTION_SYSTEM_PROMPT = """You are a Knowledge Graph Extractor. Analyze the given text and output a JSON object containing 'nodes' and 'edges'.

RULES:
1. Each node must have: "name" (string), "node_type" (one of: "concept", "entity", "document", "fact"), "description" (1-2 sentence summary).
2. Each edge must have: "source" (node name), "target" (node name), "label" (descriptive verb phrase like "uses", "relates_to", "includes", "contradicts").
3. Extract 3-8 nodes and 2-6 edges from the text.
4. Node names should be concise (1-4 words).
5. Allowed edge labels: "uses", "relates_to", "includes", "contradicts", "causes", "enables", "requires", "implements".
6. Output ONLY valid JSON — no markdown, no explanation, no preamble.

EXAMPLE OUTPUT:
{
  "nodes": [
    {"name": "Machine Learning", "node_type": "concept", "description": "Field of AI that learns from data"},
    {"name": "Neural Network", "node_type": "entity", "description": "Computing model inspired by biological neurons"}
  ],
  "edges": [
    {"source": "Machine Learning", "target": "Neural Network", "label": "includes"}
  ]
}"""

# ═══════════════════════════════════════════════════════════
#  System prompt for entity extraction from a query
# ═══════════════════════════════════════════════════════════

ENTITY_EXTRACTION_PROMPT = """Extract the main entity or concept from the user's question. 
Return ONLY a JSON object: {"entity": "the main topic"}.
If multiple entities, pick the most important one.
No markdown, no explanation."""


async def extract_graph(text: str) -> ExtractionResult:
    """
    Send text to the LLM and parse the extracted knowledge graph.
    Returns an ExtractionResult with nodes and edges.
    """
    try:
        raw = await llm_generate(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=f"Extract a knowledge graph from this text:\n\n{text[:4000]}",
            temperature=0.2,
            max_tokens=1500,
        )

        parsed = parse_json_from_llm(raw)
        if not parsed:
            logger.warning("LLM returned unparseable output for graph extraction")
            return _fallback_extraction(text)

        nodes = [
            ExtractedNode(
                name=n.get("name", "Unknown"),
                node_type=n.get("node_type", "concept"),
                description=n.get("description", ""),
            )
            for n in parsed.get("nodes", [])
        ]
        edges = [
            ExtractedEdge(
                source=e.get("source", ""),
                target=e.get("target", ""),
                label=e.get("label", "relates_to"),
            )
            for e in parsed.get("edges", [])
        ]

        return ExtractionResult(nodes=nodes, edges=edges)

    except Exception as e:
        logger.error("Graph extraction failed: %s", e)
        return _fallback_extraction(text)


async def extract_entity_from_query(query: str) -> str:
    """
    Use LLM (or regex fallback) to extract the main entity from a query.
    Used for the Graph DB retrieval path.
    """
    try:
        raw = await llm_generate(
            system_prompt=ENTITY_EXTRACTION_PROMPT,
            user_prompt=query,
            temperature=0.1,
            max_tokens=100,
        )
        parsed = parse_json_from_llm(raw)
        if parsed and "entity" in parsed:
            return parsed["entity"]
    except Exception as e:
        logger.warning("Entity extraction LLM call failed: %s", e)

    # Regex fallback: extract nouns-like words (longest capitalized phrase or NOUN-like)
    return _regex_entity_extraction(query)


def _regex_entity_extraction(query: str) -> str:
    """Simple heuristic: take the longest meaningful phrase from the query."""
    import re

    # Remove common question words
    cleaned = re.sub(
        r"\b(what|how|why|when|where|who|is|are|was|were|do|does|did|can|could|would|should|"
        r"tell|me|about|explain|describe|the|a|an|of|in|on|for|with|to|and|or)\b",
        "",
        query.lower(),
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Take first meaningful chunk
    words = [w for w in cleaned.split() if len(w) > 2]
    return " ".join(words[:3]) if words else query[:30]


def _fallback_extraction(text: str) -> ExtractionResult:
    """
    Simple keyword-based fallback when LLM is unavailable.
    Creates a single document node from the text title.
    """
    import re

    # Use first sentence as title/name
    first_sentence = re.split(r"[.!?\n]", text)[0].strip()[:60]
    if not first_sentence:
        first_sentence = "Untitled Document"

    return ExtractionResult(
        nodes=[
            ExtractedNode(
                name=first_sentence,
                node_type="document",
                description=text[:150].strip(),
            )
        ],
        edges=[],
    )
