"""
GraphMind Backend — Global In-Memory Store (CQRS Read-Model)
=============================================================
USER_GRAPHS      : user_id → adjacency list (_UserGraph)
USER_AUTOMATONS  : user_id → compiled ahocorasick.Automaton (or dict fallback)

All mutations go through _STORE_LOCK (asyncio.Lock).
The only Neo4j call: init_user_session() — called once per login.
After that, all reads are zero-database.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("graphmind.memory_store")

try:
    import ahocorasick
    _AC_AVAILABLE = True
except ImportError:
    _AC_AVAILABLE = False
    logger.warning(
        "pyahocorasick not installed — entity matching falls back to linear scan. "
        "Install with: pip install pyahocorasick"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Internal data structures
# ══════════════════════════════════════════════════════════════════════════════

class _UserGraph:
    __slots__ = ("nodes", "adj", "edge_meta")

    def __init__(self) -> None:
        self.nodes:     Dict[str, dict]              = {}
        self.adj:       Dict[str, Set[str]]           = {}
        self.edge_meta: Dict[Tuple[str, str], dict]   = {}

    def add_node(self, node_id: str, **props: Any) -> None:
        self.nodes[node_id] = props
        self.adj.setdefault(node_id, set())

    def add_edge(self, src: str, tgt: str, relation: str = "RELATED_TO",
                 reason: str = "", weight: float = 1.0,
                 is_directional: bool = True) -> None:
        self.adj.setdefault(src, set()).add(tgt)
        self.adj.setdefault(tgt, set()).add(src)   # undirected BFS view
        self.edge_meta[(src, tgt)] = {"relation": relation, "reason": reason, "weight": weight}
        if not is_directional:
            self.edge_meta[(tgt, src)] = {"relation": relation, "reason": reason, "weight": weight}

    def __len__(self) -> int:
        return len(self.nodes)


# ══════════════════════════════════════════════════════════════════════════════
# Module-level singletons
# ══════════════════════════════════════════════════════════════════════════════

_USER_GRAPHS:     Dict[str, _UserGraph] = {}
_USER_AUTOMATONS: Dict[str, Any]         = {}
_STORE_LOCK = asyncio.Lock()


# ══════════════════════════════════════════════════════════════════════════════
# Neo4j loader
# ══════════════════════════════════════════════════════════════════════════════

_LOAD_CYPHER = """
MATCH (n)
WHERE (n:Entity OR n:Category OR n:Fact OR n:Content OR n:Request)
  AND (n.user_id = $user_id)
WITH n
OPTIONAL MATCH (n)-[r]-(m)
WHERE (m:Entity OR m:Category OR m:Fact OR m:Content OR m:Request)
  AND (m.user_id = $user_id)
RETURN
  COALESCE(n.name, n.node_id, id(n) + '')        AS src_id,
  COALESCE(n.display_name, n.name, '')            AS src_display,
  COALESCE(n.category, labels(n)[0], 'entity')    AS src_category,
  COALESCE(n.domain, 'General')                   AS src_domain,
  COALESCE(n.snippet, n.content, '')              AS src_snippet,
  COALESCE(m.name, m.node_id, '')                 AS tgt_id,
  COALESCE(m.display_name, m.name, '')            AS tgt_display,
  COALESCE(m.category, labels(m)[0], 'entity')    AS tgt_category,
  COALESCE(m.domain, 'General')                   AS tgt_domain,
  COALESCE(m.snippet, m.content, '')              AS tgt_snippet,
  type(r)                                         AS rel_type,
  COALESCE(r.reason, '')                          AS rel_reason,
  COALESCE(r.weight, 1.0)                         AS rel_weight,
  COALESCE(r.is_directional, true)                AS rel_dir
"""


def _build_graph(records: List[dict]) -> _UserGraph:
    g = _UserGraph()
    for row in records:
        src = (row.get("src_id") or "").strip().lower()
        if not src:
            continue
        if src not in g.nodes:
            g.add_node(src,
                display  = row.get("src_display") or src,
                category = (row.get("src_category") or "entity").lower(),
                domain   = row.get("src_domain") or "General",
                snippet  = row.get("src_snippet") or "",
            )
        tgt = (row.get("tgt_id") or "").strip().lower()
        if not tgt:
            continue
        if tgt not in g.nodes:
            g.add_node(tgt,
                display  = row.get("tgt_display") or tgt,
                category = (row.get("tgt_category") or "entity").lower(),
                domain   = row.get("tgt_domain") or "General",
                snippet  = row.get("tgt_snippet") or "",
            )
        g.add_edge(src, tgt,
            relation       = row.get("rel_type") or "RELATED_TO",
            reason         = row.get("rel_reason") or "",
            weight         = float(row.get("rel_weight") or 1.0),
            is_directional = bool(row.get("rel_dir", True)),
        )
    return g


def _build_automaton(graph: _UserGraph) -> Any:
    if _AC_AVAILABLE:
        A = ahocorasick.Automaton()
        for node_id, props in graph.nodes.items():
            A.add_word(node_id, node_id)
            display = (props.get("display") or "").lower()
            if display and display != node_id:
                A.add_word(display, node_id)
        if len(A):
            A.make_automaton()
        return A
    else:
        mapping: Dict[str, str] = {}
        for node_id, props in graph.nodes.items():
            mapping[node_id] = node_id
            display = (props.get("display") or "").lower()
            if display:
                mapping[display] = node_id
        return mapping


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

async def init_user_session(user_id: str, driver: Any) -> Tuple[int, int, float]:
    """
    Load user's full graph from Neo4j into RAM once.
    Returns (node_count, automaton_keys_approx, elapsed_ms).
    """
    t0 = time.perf_counter()

    def _fetch() -> List[dict]:
        with driver.session() as session:
            return [r.data() for r in session.run(_LOAD_CYPHER, {"user_id": user_id})]

    records  = await asyncio.to_thread(_fetch)
    graph    = _build_graph(records)
    automaton = _build_automaton(graph)

    async with _STORE_LOCK:
        _USER_GRAPHS[user_id]     = graph
        _USER_AUTOMATONS[user_id] = automaton

    elapsed = (time.perf_counter() - t0) * 1_000
    logger.info("Session init: user=%s nodes=%d time=%.1fms", user_id, len(graph), elapsed)
    return len(graph), len(graph) * 2, elapsed


def scan_query(user_id: str, query: str) -> List[str]:
    """O(N) entity match via Aho-Corasick (or fallback linear scan)."""
    automaton = _USER_AUTOMATONS.get(user_id)
    if automaton is None:
        return []
    q = query.lower()
    if _AC_AVAILABLE and hasattr(automaton, "iter"):
        seen: Set[str] = set()
        for _, node_id in automaton.iter(q):
            seen.add(node_id)
        return list(seen)
    else:
        return [nid for kw, nid in automaton.items() if kw in q]


def bfs_subgraph(user_id: str, seed_ids: List[str],
                  max_hops: int = 2, max_nodes: int = 80) -> Tuple[List[dict], List[dict]]:
    """Multi-source BFS on RAM adjacency list. O(V+E) within hop budget."""
    graph = _USER_GRAPHS.get(user_id)
    if graph is None or not seed_ids:
        return [], []

    visited:  Set[str]                  = set()
    frontier: deque                     = deque()
    edge_set: Set[Tuple[str, str]]      = set()

    for sid in seed_ids:
        sl = sid.lower()
        if sl in graph.nodes and sl not in visited:
            visited.add(sl)
            frontier.append((sl, 0))

    result_nodes: List[dict] = []
    result_edges: List[dict] = []

    while frontier:
        node_id, depth = frontier.popleft()
        props = graph.nodes.get(node_id, {})
        result_nodes.append({"node_id": node_id, **props})

        if depth >= max_hops:
            continue

        for nb in graph.adj.get(node_id, set()):
            ekey = (min(node_id, nb), max(node_id, nb))
            if ekey not in edge_set:
                edge_set.add(ekey)
                meta = graph.edge_meta.get((node_id, nb)) or graph.edge_meta.get((nb, node_id)) or {}
                result_edges.append({
                    "source": node_id, "target": nb,
                    "relation": meta.get("relation", "RELATED_TO"),
                    "reason":   meta.get("reason", ""),
                    "weight":   meta.get("weight", 1.0),
                })
            if nb not in visited:
                visited.add(nb)
                frontier.append((nb, depth + 1))
            if len(visited) >= max_nodes:
                return result_nodes, result_edges

    return result_nodes, result_edges


def assemble_context(nodes: List[dict], edges: List[dict]) -> str:
    """Format BFS subgraph into an LLM context string. Pure CPU — no I/O."""
    if not nodes:
        return "(No memory context found)"
    lines = ["=== Graph Memory Context ===\n"]
    by_domain: Dict[str, List[dict]] = {}
    for n in nodes:
        by_domain.setdefault(n.get("domain", "General"), []).append(n)
    for domain, dnodes in by_domain.items():
        lines.append(f"--- {domain} ---")
        for n in dnodes:
            line = f"  [{n.get('category','entity').upper()}] {n.get('display') or n['node_id']}"
            if n.get("snippet"):
                line += f": {n['snippet']}"
            lines.append(line)
        lines.append("")
    if edges:
        lines.append("--- Relationships ---")
        nmap = {n["node_id"]: n.get("display") or n["node_id"] for n in nodes}
        for e in edges[:40]:
            lines.append(
                f"  {nmap.get(e['source'], e['source'])} "
                f"--[{e['relation']}]--> "
                f"{nmap.get(e['target'], e['target'])}"
                + (f"  ({e['reason']})" if e.get("reason") else "")
            )
    return "\n".join(lines)


async def update_user_graph(user_id: str, new_nodes: List[dict],
                             new_edges: List[dict]) -> None:
    """Incrementally patch the RAM graph + recompile automaton under the lock."""
    async with _STORE_LOCK:
        graph = _USER_GRAPHS.get(user_id)
        if graph is None:
            return
        for n in new_nodes:
            nid = (n.get("node_id") or n.get("name") or "").lower()
            if nid and nid not in graph.nodes:
                graph.add_node(nid,
                    display  = n.get("display") or n.get("name") or nid,
                    category = n.get("category") or "entity",
                    domain   = n.get("domain") or "General",
                    snippet  = n.get("snippet") or "",
                )
        for e in new_edges:
            src = (e.get("source") or "").lower()
            tgt = (e.get("target") or "").lower()
            if src and tgt:
                graph.add_edge(src, tgt,
                    relation       = e.get("relation", "RELATED_TO"),
                    reason         = e.get("reason", ""),
                    weight         = float(e.get("weight", 1.0)),
                    is_directional = bool(e.get("is_directional", True)),
                )
        _USER_AUTOMATONS[user_id] = _build_automaton(graph)


def get_graph_stats(user_id: str) -> dict:
    graph = _USER_GRAPHS.get(user_id)
    if graph is None:
        return {"loaded": False, "nodes": 0, "edges": 0}
    return {
        "loaded": True,
        "nodes":  len(graph),
        "edges":  sum(len(v) for v in graph.adj.values()) // 2,
    }


def drop_user_session(user_id: str) -> None:
    _USER_GRAPHS.pop(user_id, None)
    _USER_AUTOMATONS.pop(user_id, None)
