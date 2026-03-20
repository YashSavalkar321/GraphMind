"""
GraphMind Backend — Background Worker (CQRS Write Path)
========================================================
extract_and_sync_graph(user_id, query, driver, llm_fn)
  1. LLM extracts 4-category nodes (content/request/entity/fact) + justified edges.
  2. Subset-rule dedup against current RAM graph.
  3. Parameterised MERGE Cypher → Neo4j (in thread pool).
  4. Patches RAM adjacency list + recompiles Aho-Corasick automaton.

Never called on the critical path — only via FastAPI BackgroundTasks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any, Callable, List, Optional

from memory_store import _USER_GRAPHS, update_user_graph
from vector_store import get_node_embedding

logger = logging.getLogger("graphmind.worker")


# ══════════════════════════════════════════════════════════════════════════════
# Extraction prompt
# ══════════════════════════════════════════════════════════════════════════════

EXTRACTION_SYSTEM_PROMPT = """\
You are a Knowledge Graph Builder for a personal assistant.

Analyse the USER TEXT and return a JSON object with EXACTLY two keys:

{
  "nodes": [...],
  "edges": [...]
}

NODE SCHEMA (each item in "nodes"):
  "name"          : canonical, lower-cased, no punctuation
  "display"       : original casing (can equal name)
  "node_category" : one of ["entity","preference","fact","event","goal"]
  "domain"        : one of ["Health","Finance","Learning","Work","Travel","Personal","General"]
  "snippet"       : 1–2 sentence context excerpt
  "properties"    : {} or flat dict of extra attributes

CATEGORY RULES (use the FIRST matching rule):
  1. goal       → user WANTS, PLANS, AIMS, or INTENDS to do something in the future
                  Examples: "want to learn React", "aiming for a promotion",
                  "planning to travel to Japan", "get a full-stack developer job"
  2. preference → user LIKES, DISLIKES, PREFERS, LOVES, HATES, or does HABITUALLY
                  Examples: "love playing badminton", "prefer dark mode",
                  "hate waking up early", "enjoy coding at night"
  3. event      → something that HAPPENED or WILL HAPPEN at a time/place
                  Examples: "went to Mumbai last week", "attended a hackathon",
                  "won first prize", "graduated in 2023"
  4. fact       → a declarative statement about the user's state, ability, or attribute
                  Examples: "I am good at DSA", "I know Python",
                  "I am allergic to peanuts", "I have 2 years of experience"
  5. entity     → a named person, place, organization, technology, or specific thing
                  that is NOT better classified by rules 1-4 above
                  Examples: "Python", "React", "Mumbai", "Google", "PCCOE"

PRIORITY: If a node could match multiple categories, pick the FIRST match
from rules 1→5. For example:
  • "badminton" in "I love playing badminton" → preference (rule 2), NOT entity
  • "React" in "I want to learn React" → "React" is entity (rule 5),
    but also create a goal node "learn react" (rule 1)
  • "hackathon" in "I went to a hackathon" → event (rule 3), NOT entity
  • "DSA" in "I am good at DSA" → "DSA" is entity (rule 5),
    but also create a fact "good at dsa" (rule 4)

EDGE SCHEMA (each item in "edges"):
  "source"         : canonical node name (must be in "nodes")
  "target"         : canonical node name (must be in "nodes")
  "relation"       : UPPER_SNAKE_CASE (e.g. LEARNS, HAS_SKILL, WORKS_AT)
  "is_directional" : true/false
  "reason"         : exactly 1 sentence explaining why this edge exists
  "weight"         : float 0.0–1.0 (default 1.0)

SUBSET RULE: Do NOT create a new node if it is a sub-concept of an
existing node listed in KNOWN_ENTITIES. Link to the existing node instead.

QUESTION RULE: If the text is purely a question with no declarative facts,
return: {"nodes": [], "edges": []}

Output ONLY the JSON — no markdown, no commentary.
"""


def _parse(raw: str) -> Optional[dict]:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    logger.error("Worker: could not parse extraction JSON:\n%.400s", raw)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Neo4j MERGE helpers
# ══════════════════════════════════════════════════════════════════════════════

_LABEL_MAP = {
    "entity": "Entity", "preference": "Entity", "event": "Entity",
    "goal": "Entity", "message": "Entity", "document_chunk": "Entity",
    "fact": "Fact",
    # Legacy mappings (backward compat)
    "content": "Entity", "request": "Entity",
}

_MERGE_NODE = """
MERGE (n:{label} {{name: toLower($name), user_id: $uid}})
ON CREATE SET n.display=$display, n.node_id=$node_id, n.category=$cat,
              n.domain=$domain, n.snippet=$snippet, n.embedding=$embedding,
              n.user_id=$uid, n.created_at=datetime(), n.updated_at=datetime()
ON MATCH  SET n.updated_at=datetime(),
              n.snippet=CASE WHEN $snippet <> '' THEN $snippet ELSE n.snippet END,
              n.display=CASE WHEN $display <> '' THEN $display ELSE n.display END,
              n.embedding=CASE WHEN $embedding IS NOT NULL THEN $embedding ELSE n.embedding END
"""

_MERGE_EDGE_DIR = """
MATCH (s {{name: toLower($src), user_id: $uid}})
MATCH (t {{name: toLower($tgt), user_id: $uid}})
MERGE (s)-[r:{rel}]->(t)
ON CREATE SET r.reason=$reason, r.weight=$weight, r.is_directional=true,  r.created_at=datetime()
ON MATCH  SET r.weight=CASE WHEN $weight>r.weight THEN $weight ELSE r.weight END,
              r.reason=CASE WHEN $reason<>'' THEN $reason ELSE r.reason END
"""

_MERGE_EDGE_UNDIR = """
MATCH (s {{name: toLower($src), user_id: $uid}})
MATCH (t {{name: toLower($tgt), user_id: $uid}})
MERGE (s)-[r:{rel}]-(t)
ON CREATE SET r.reason=$reason, r.weight=$weight, r.is_directional=false, r.created_at=datetime()
ON MATCH  SET r.weight=CASE WHEN $weight>r.weight THEN $weight ELSE r.weight END,
              r.reason=CASE WHEN $reason<>'' THEN $reason ELSE r.reason END
"""


def _run_merges(driver: Any, uid: str, nodes: List[dict], edges: List[dict]) -> None:
    with driver.session() as session:
        for n in nodes:
            label  = _LABEL_MAP.get(n.get("node_category", "entity"), "Entity")
            cypher = _MERGE_NODE.replace("{label}", label)
            # Compute embedding for this node
            emb = get_node_embedding({
                "display": n.get("display") or n.get("name", ""),
                "snippet": n.get("snippet", ""),
            })
            try:
                session.run(cypher, {
                    "name":    n["name"].lower(),
                    "display": n.get("display") or n["name"],
                    "node_id": n["name"].lower(),
                    "cat":     n.get("node_category", "entity"),
                    "domain":  n.get("domain", "General"),
                    "snippet": n.get("snippet", ""),
                    "embedding": emb,
                    "uid":     uid,
                })
            except Exception as exc:
                logger.warning("MERGE node failed (%s): %s", n.get("name"), exc)

        for e in edges:
            rel = re.sub(r"[^A-Z0-9_]", "_", e["relation"].upper()) or "RELATED_TO"
            tmpl  = _MERGE_EDGE_DIR if e.get("is_directional", True) else _MERGE_EDGE_UNDIR
            cypher = tmpl.replace("{rel}", rel)
            try:
                session.run(cypher, {
                    "src": e["source"].lower(), "tgt": e["target"].lower(),
                    "reason": e.get("reason", ""), "weight": float(e.get("weight", 1.0)),
                    "uid": uid,
                })
            except Exception as exc:
                logger.warning("MERGE edge failed (%s→%s): %s", e["source"], e["target"], exc)

        # ── Create mindmap hierarchy: User → Category → Entity ────────
        #    This ensures the mindmap visualization (get_user_graph) can
        #    traverse User -[:HAS_CATEGORY]-> Category -[:CONTAINS]-> Entity
        _VALID_CATEGORIES = {
            "Health", "Finance", "Learning", "Work", "Travel", "Personal", "General"
        }
        # Collect entity names for HAS_FACT linking
        entity_names = [
            n["name"].lower() for n in nodes
            if n.get("node_category", "entity") != "fact"
        ]
        try:
            # Ensure User node exists
            session.run(
                "MERGE (u:User {user_id: $uid}) "
                "ON CREATE SET u.name = $uid, u.created_at = datetime()",
                {"uid": uid},
            )
            for n in nodes:
                name = n["name"].lower()
                domain = n.get("domain", "General").strip()
                if domain not in _VALID_CATEGORIES:
                    domain = "General"
                node_category = n.get("node_category", "entity")

                if node_category != "fact":
                    # All non-fact types → User → Category → Entity hierarchy
                    session.run(
                        "MATCH (u:User {user_id: $uid}) "
                        "MERGE (cat:Category {name: $category, user_id: $uid}) "
                        "  ON CREATE SET cat.created_at = datetime() "
                        "MERGE (u)-[:HAS_CATEGORY]->(cat) "
                        "MERGE (e:Entity {name: $name, user_id: $uid}) "
                        "  ON CREATE SET e.type = $etype, e.category = $category, "
                        "               e.last_accessed = datetime() "
                        "  ON MATCH SET e.last_accessed = datetime(), "
                        "              e.category = $category "
                        "MERGE (cat)-[:CONTAINS]->(e)",
                        {
                            "uid": uid,
                            "name": name,
                            "category": domain,
                            "etype": node_category.capitalize(),
                        },
                    )
                else:
                    # Fact nodes → link to related entities via HAS_FACT
                    if entity_names:
                        session.run(
                            "MERGE (f:Fact {name: $name, user_id: $uid}) "
                            "  ON CREATE SET f.snippet = $snippet, "
                            "               f.created_at = datetime() "
                            "  ON MATCH SET f.snippet = CASE WHEN $snippet <> '' "
                            "    THEN $snippet ELSE f.snippet END "
                            "WITH f "
                            "UNWIND $entity_names AS ename "
                            "MATCH (e:Entity {name: ename, user_id: $uid}) "
                            "MERGE (e)-[:HAS_FACT]->(f)",
                            {
                                "uid": uid,
                                "name": name,
                                "snippet": n.get("snippet", ""),
                                "entity_names": entity_names,
                            },
                        )
        except Exception as exc:
            logger.warning("Hierarchy creation failed (non-fatal): %s", exc)

        # Invalidate mindmap cache so frontend sees new nodes immediately
        try:
            from memory_ops import invalidate_cache
            invalidate_cache(uid)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Subset-rule dedup
# ══════════════════════════════════════════════════════════════════════════════

def _dedup(nodes: List[dict], edges: List[dict], known: set) -> tuple:
    remap: dict = {}
    for n in nodes:
        cand  = n["name"].lower()
        cwords = set(cand.split())
        for ex in known:
            exw = set(ex.split())
            if cwords and cwords.issubset(exw):
                remap[cand] = ex; break
            if ex in cand and len(cand.split()) <= 3:
                remap[cand] = ex; break

    kept_nodes = [n for n in nodes if n["name"].lower() not in remap]
    kept_edges: List[dict] = []
    for e in edges:
        src = remap.get(e["source"].lower(), e["source"])
        tgt = remap.get(e["target"].lower(), e["target"])
        if src != tgt:
            kept_edges.append({**e, "source": src, "target": tgt})

    return kept_nodes, kept_edges


# ══════════════════════════════════════════════════════════════════════════════
# Main task
# ══════════════════════════════════════════════════════════════════════════════

async def extract_and_sync_graph(
    user_id: str,
    query:   str,
    driver:  Any,
    llm_fn:  Callable[[str, str], Any],
) -> None:
    """
    Fire-and-forget background task.
    1. LLM extraction  2. Subset dedup  3. Neo4j MERGE  4. RAM update
    """
    t0 = time.perf_counter()

    graph = _USER_GRAPHS.get(user_id)
    known = set(graph.nodes.keys()) if graph else set()
    known_hint = ", ".join(sorted(known)[:120]) or "none"

    user_prompt = (
        f"KNOWN_ENTITIES (do not duplicate): [{known_hint}]\n\n"
        f"USER TEXT:\n{query}"
    )
    try:
        raw = await llm_fn(EXTRACTION_SYSTEM_PROMPT, user_prompt)
    except Exception as exc:
        logger.error("Worker LLM call failed (user=%s): %s", user_id, exc)
        return

    obj = _parse(raw)
    if not obj or (not obj.get("nodes") and not obj.get("edges")):
        return

    nodes, edges = _dedup(obj.get("nodes", []), obj.get("edges", []), known)

    try:
        await asyncio.to_thread(_run_merges, driver, user_id, nodes, edges)
    except Exception as exc:
        logger.error("Worker Neo4j MERGE failed (user=%s): %s", user_id, exc)
        return

    # Build RAM nodes with embeddings attached for vector_store
    ram_nodes = []
    for n in nodes:
        node_dict = {
            "node_id": n["name"].lower(),
            "display": n.get("display") or n["name"],
            "category": n.get("node_category", "entity"),
            "domain": n.get("domain", "General"),
            "snippet": n.get("snippet", ""),
        }
        # Pre-compute embedding so update_user_vectors can skip re-embedding
        emb = get_node_embedding(node_dict)
        if emb:
            node_dict["embedding"] = emb
        ram_nodes.append(node_dict)

    ram_edges = [{"source": e["source"].lower(), "target": e["target"].lower(),
                  "relation": e["relation"], "reason": e.get("reason", ""),
                  "weight": e.get("weight", 1.0), "is_directional": e.get("is_directional", True)}
                 for e in edges]
    await update_user_graph(user_id, ram_nodes, ram_edges)

    elapsed = (time.perf_counter() - t0) * 1_000
    logger.info("Worker done: user=%s +%d nodes +%d edges → %.1fms",
                user_id, len(nodes), len(edges), elapsed)
