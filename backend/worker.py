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

from backend.memory_store import _USER_GRAPHS, update_user_graph

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
  "node_category" : one of ["content","request","entity","fact"]
                    • content  = concept, topic, technology, idea
                    • request  = user intention, goal, task
                    • entity   = real-world object (person, place, org)
                    • fact     = concrete verifiable claim
  "domain"        : one of ["Health","Finance","Learning","Work","Travel","Personal","General"]
  "snippet"       : 1–2 sentence context excerpt
  "properties"    : {} or flat dict of extra attributes

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

_LABEL_MAP = {"content": "Content", "request": "Request", "entity": "Entity", "fact": "Fact"}

_MERGE_NODE = """
MERGE (n:{label} {{name: toLower($name), user_id: $uid}})
ON CREATE SET n.display=$display, n.node_id=$node_id, n.category=$cat,
              n.domain=$domain, n.snippet=$snippet,
              n.user_id=$uid, n.created_at=datetime(), n.updated_at=datetime()
ON MATCH  SET n.updated_at=datetime(),
              n.snippet=CASE WHEN $snippet <> '' THEN $snippet ELSE n.snippet END,
              n.display=CASE WHEN $display <> '' THEN $display ELSE n.display END
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
            try:
                session.run(cypher, {
                    "name":    n["name"].lower(),
                    "display": n.get("display") or n["name"],
                    "node_id": n["name"].lower(),
                    "cat":     n.get("node_category", "entity"),
                    "domain":  n.get("domain", "General"),
                    "snippet": n.get("snippet", ""),
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

    ram_nodes = [{"node_id": n["name"].lower(), "display": n.get("display") or n["name"],
                  "category": n.get("node_category", "entity"), "domain": n.get("domain", "General"),
                  "snippet": n.get("snippet", "")} for n in nodes]
    ram_edges = [{"source": e["source"].lower(), "target": e["target"].lower(),
                  "relation": e["relation"], "reason": e.get("reason", ""),
                  "weight": e.get("weight", 1.0), "is_directional": e.get("is_directional", True)}
                 for e in edges]
    await update_user_graph(user_id, ram_nodes, ram_edges)

    elapsed = (time.perf_counter() - t0) * 1_000
    logger.info("Worker done: user=%s +%d nodes +%d edges → %.1fms",
                user_id, len(nodes), len(edges), elapsed)
