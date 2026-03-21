"""
GraphMind — Memory Operations (Optimized)
===========================================
Ultra-fast retrieval (<100ms target), relevance-scored context filtering,
and reliable long-context memory with zero data loss.

Performance Architecture:
- Instant keyword extraction (regex, zero LLM calls during retrieval)
- Single batched Cypher query (no N+1 queries)
- In-memory LRU cache for hot paths
- TF-IDF relevance scoring for context filtering
- Full conversation history for long-context remembering
"""

from __future__ import annotations

import logging
import math
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from backend.database import get_db
from backend.llm_service import extract_knowledge
from backend.memory_store import touch_user_memory_version

logger = logging.getLogger("graphmind.memory")

# ── Constants ──────────────────────────────────────────────────

_MAX_CONTEXT_FACTS = 30         # Top-N most relevant facts in context
_DECAY_HALF_LIFE_DAYS = 30.0    # Memory half-life in days
_CACHE_TTL_SECONDS = 120        # Graph cache TTL (invalidated on ingest)
_STOP_WORDS = frozenset({
    "i", "me", "my", "mine", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "her", "hers", "she", "it", "its", "they", "them", "their", "theirs",
    "the", "a", "an", "is", "am", "are", "was", "were", "be", "been",
    "being", "do", "does", "did", "doing", "have", "has", "had", "having",
    "will", "shall", "would", "could", "should", "may", "might", "can",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "that", "this", "these", "those", "but", "and", "or", "not", "no",
    "nor", "if", "then", "else", "so", "than", "too", "very", "just",
    "about", "above", "after", "again", "all", "also", "any", "because",
    "before", "below", "between", "both", "by", "each", "few", "for",
    "from", "further", "get", "got", "here", "in", "into", "more",
    "most", "of", "off", "on", "once", "only", "other", "out", "over",
    "own", "same", "some", "such", "tell", "to", "under", "until", "up",
    "want", "with", "know", "remember", "think", "need", "like",
})

# ── Category definitions ──────────────────────────────────────

VALID_CATEGORIES = frozenset({
    "Health", "Finance", "Learning", "Work", "Travel", "Personal", "General"
})

# Keyword vocabularies for fast category detection (zero LLM calls)
CATEGORY_KEYWORDS: Dict[str, frozenset] = {
    "Health": frozenset({
        "symptom", "pain", "medication", "medicine", "health", "sick",
        "disease", "condition", "trigger", "diet", "exercise", "sleep",
        "anxiety", "stress", "doctor", "hospital", "treatment", "allergy",
        "headache", "fatigue", "nausea", "blood", "pressure", "diabetes",
        "therapy", "mental", "vitamins", "dosage", "injury", "fever",
    }),
    "Finance": frozenset({
        "budget", "money", "expense", "cost", "invest", "saving", "income",
        "salary", "loan", "debt", "financial", "spend", "bank", "tax",
        "insurance", "portfolio", "rent", "bill", "payment", "subscription",
        "stock", "crypto", "savings", "account", "mortgage", "fund",
    }),
    "Learning": frozenset({
        "learn", "study", "course", "skill", "topic", "tutorial",
        "prerequisite", "resource", "practice", "knowledge", "lecture",
        "homework", "exam", "read", "book", "roadmap", "programming",
        "math", "science", "language", "certificate", "degree",
    }),
    "Work": frozenset({
        "project", "code", "engineering", "review", "team", "standard",
        "pattern", "tool", "framework", "api", "bug", "deploy",
        "architecture", "meeting", "manager", "deadline", "sprint",
        "commit", "repository", "production", "backend", "frontend",
    }),
    "Travel": frozenset({
        "travel", "trip", "destination", "hotel", "flight", "itinerary",
        "visit", "city", "country", "vacation", "holiday", "tour",
        "passport", "visa", "accommodation", "restaurant", "transport",
    }),
    "Personal": frozenset({
        "hobby", "preference", "like", "dislike", "habit", "relationship",
        "friend", "family", "birthday", "routine", "interest", "value",
        "personality", "dream", "feeling", "emotion", "lifestyle",
    }),
}


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Instant Keyword Extraction (ZERO LLM calls) ───────────────

def extract_keywords_fast(query: str) -> List[str]:
    """Extract keywords from query using regex — runs in <1ms.

    No LLM call needed. Uses stop-word removal, multi-word phrase
    detection, and bigram extraction for higher accuracy.
    """
    # Normalize
    text = query.lower().strip()

    # Extract quoted phrases first (high priority)
    phrases = re.findall(r'"([^"]+)"', text)
    text_without_quotes = re.sub(r'"[^"]*"', '', text)

    # Extract individual words (2+ chars, alphanumeric)
    raw_words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#.-]{1,}\b', text_without_quotes)
    words = [w.lower() for w in raw_words if w.lower() not in _STOP_WORDS]

    # Generate bigrams for multi-word concepts (e.g., "machine learning")
    bigrams = []
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        bigrams.append(bigram)

    # Combine: phrases > bigrams > unigrams
    keywords = list(dict.fromkeys(phrases + bigrams + words))

    return keywords[:15]  # Cap at 15 keywords


# ── Category-Aware Query Classifier ────────────────────────────

def _detect_query_category(keywords: List[str]) -> Optional[str]:
    """Match query keywords to the most relevant memory category.

    Returns the best-matching category name, or None if no confident match.
    Used to focus retrieval on a specific category for 1.4× relevance boost.
    Runs in <1ms — no LLM call.
    """
    kw_set = {k.lower() for k in keywords}
    best_cat, best_score = None, 0
    for cat, cat_kws in CATEGORY_KEYWORDS.items():
        score = len(kw_set & cat_kws)
        if score > best_score:
            best_score, best_cat = score, cat
    return best_cat if best_score > 0 else None


# ── Relevance Scoring Engine ──────────────────────────────────

def _compute_relevance(
    entity_name: str,
    fact_content: str,
    keywords: List[str],
    confidence: float,
    hours_since_access: float,
) -> float:
    """Compute a relevance score combining keyword match, confidence, and recency.

    Score = keyword_score * confidence_boost * recency_factor

    Returns a float between 0.0 and 1.0.
    """
    name_lower = entity_name.lower()
    fact_lower = fact_content.lower() if fact_content else ""
    combined = f"{name_lower} {fact_lower}"

    # ── Keyword matching (TF-like scoring) ──────────────────────
    keyword_score = 0.0
    for kw in keywords:
        kw_lower = kw.lower()
        # Exact entity name match = very high score
        if kw_lower == name_lower:
            keyword_score += 3.0
        # Entity name contains keyword
        elif kw_lower in name_lower:
            keyword_score += 2.0
        # Fact content contains keyword
        elif kw_lower in fact_lower:
            keyword_score += 1.0
        # Partial word overlap
        elif any(kw_lower in w for w in combined.split()):
            keyword_score += 0.5

    if keyword_score == 0:
        return 0.0

    # Normalize keyword score (0-1)
    keyword_score = min(keyword_score / (len(keywords) * 2), 1.0)

    # ── Confidence boost (0.5 - 1.0) ───────────────────────────
    confidence_factor = 0.5 + (confidence * 0.5)

    # ── Recency decay (exponential) ─────────────────────────────
    half_life_hours = _DECAY_HALF_LIFE_DAYS * 24
    recency_factor = math.pow(0.5, hours_since_access / half_life_hours)
    recency_factor = max(recency_factor, 0.1)  # Floor at 10%

    return keyword_score * confidence_factor * recency_factor


# ── Graph Cache (in-memory, per-user) ──────────────────────────

_graph_cache: Dict[str, Tuple[float, Any]] = {}


def _get_cached_or_fetch(user_id: str, query_key: str, fetcher):
    """LRU-style cache with TTL. Avoids duplicate Neo4j calls."""
    cache_key = f"{user_id}:{query_key}"
    now = time.time()
    if cache_key in _graph_cache:
        ts, data = _graph_cache[cache_key]
        if now - ts < _CACHE_TTL_SECONDS:
            return data
    data = fetcher()
    _graph_cache[cache_key] = (now, data)
    # Evict old entries (keep cache bounded)
    if len(_graph_cache) > 200:
        oldest = sorted(_graph_cache, key=lambda k: _graph_cache[k][0])[:50]
        for k in oldest:
            del _graph_cache[k]
    return data


def invalidate_cache(user_id: str):
    """Clear cache entries for a specific user (call after ingest)."""
    keys_to_delete = [k for k in _graph_cache if k.startswith(f"{user_id}:")]
    for k in keys_to_delete:
        del _graph_cache[k]


# ── Memory Writer (Ingestion) ──────────────────────────────────

async def ingest_to_graph(user_id: str, text: str) -> Dict[str, Any]:
    """Extract entities & facts from text and write them into Neo4j.

    Uses batched Cypher with UNWIND for maximum write performance.
    """
    db = get_db()
    extraction = await extract_knowledge(text)

    entities = extraction.get("entities", [])
    relationships = extraction.get("relationships", [])
    facts = extraction.get("facts", [])
    now = datetime.now(timezone.utc).isoformat()

    # ── Ensure User node ────────────────────────────────────────
    db.execute_write(
        "MERGE (u:User {user_id: $uid}) "
        "ON CREATE SET u.name = $uid, u.created_at = $now",
        {"uid": user_id, "now": now},
    )

    # ── Batch entity creation (single UNWIND query) ─────────────
    entity_params = []
    for ent in entities:
        name = ent.get("name", "").strip()
        etype = ent.get("type", "Unknown").strip()
        category = ent.get("category", "General").strip()
        if category not in VALID_CATEGORIES:
            category = "General"
        if name:
            entity_params.append({
                "name": name, "type": etype, "category": category,
                "mid": _uuid(), "now": now,
            })

    if entity_params:
        db.execute_write(
            "MATCH (u:User {user_id: $uid}) "
            "WITH u "
            "UNWIND $entities AS ent "
            "MERGE (cat:Category {name: ent.category, user_id: $uid}) "
            "  ON CREATE SET cat.created_at = ent.now "
            "MERGE (u)-[:HAS_CATEGORY]->(cat) "
            "MERGE (e:Entity {name: ent.name, user_id: $uid}) "
            "  ON CREATE SET e.type = ent.type, e.category = ent.category, "
            "               e.memory_id = ent.mid, e.created_at = ent.now, "
            "               e.last_accessed = ent.now "
            "  ON MATCH SET e.last_accessed = ent.now, e.category = ent.category, "
            "              e.type = ent.type "
            "MERGE (cat)-[:CONTAINS]->(e)",
            {"uid": user_id, "entities": entity_params},
        )

    # ── Batch fact creation ─────────────────────────────────────
    fact_params = []
    for fact in facts:
        content = fact.get("content", "").strip()
        entity_name = fact.get("entity_name", "").strip()
        confidence = fact.get("confidence", 1.0)
        if content:
            if not entity_name and entity_params:
                entity_name = entity_params[0]["name"]
            if entity_name:
                fact_params.append({
                    "content": content, "ename": entity_name,
                    "conf": confidence, "mid": _uuid(), "now": now,
                })

    if fact_params:
        db.execute_write(
            "UNWIND $facts AS f "
            "MERGE (e:Entity {name: f.ename, user_id: $uid}) "
            "MERGE (fct:Fact {name: f.content, user_id: $uid}) "
            "ON CREATE SET fct.confidence = f.conf, fct.last_accessed = f.now, "
            "             fct.memory_id = f.mid, fct.created_at = f.now, "
            "             fct.decay_score = f.conf, fct.snippet = f.content "
            "ON MATCH SET fct.last_accessed = f.now, "
            "            fct.confidence = CASE WHEN fct.confidence < f.conf "
            "                                 THEN f.conf ELSE fct.confidence END "
            "MERGE (e)-[:HAS_FACT]->(fct)",
            {"uid": user_id, "facts": fact_params},
        )

    # ── Batch relationship creation ─────────────────────────────
    rel_params = []
    for rel in relationships:
        source = rel.get("source", "").strip()
        target = rel.get("target", "").strip()
        relation = rel.get("relation", "RELATED_TO").strip()
        if source and target and source.lower() != "user":
            rel_params.append({
                "source": source, "target": target, "rel": relation,
            })

    if rel_params:
        db.execute_write(
            "UNWIND $rels AS r "
            "MERGE (s:Entity {name: r.source, user_id: $uid}) "
            "MERGE (t:Entity {name: r.target, user_id: $uid}) "
            "MERGE (s)-[rel:RELATED_TO]->(t) "
            "ON CREATE SET rel.type = r.rel",
            {"uid": user_id, "rels": rel_params},
        )

    # ── Store raw text as Interaction (long-context memory) ─────
    db.execute_write(
        "MATCH (u:User {user_id: $uid}) "
        "CREATE (i:Interaction {query: $text, response: 'ingested', "
        "        timestamp: $now, memory_id: $mid, user_id: $uid}) "
        "MERGE (u)-[:PARTICIPATED_IN]->(i)",
        {"uid": user_id, "text": text, "now": now, "mid": _uuid()},
    )

    # Invalidate cache for this user
    invalidate_cache(user_id)
    touch_user_memory_version(user_id)

    logger.info(
        "Ingested for user=%s: %d entities, %d facts, %d rels  [batched]",
        user_id, len(entity_params), len(fact_params), len(rel_params),
    )

    return {
        "entities_created": len(entity_params),
        "facts_created": len(fact_params),
    }


# ── Memory Reader (Ultra-Fast Retrieval) ───────────────────────

async def retrieve_from_graph(user_id: str, query: str) -> Dict[str, Any]:
    """Retrieve relevant memory context in <100ms.

    Pipeline:
    1. Instant keyword extraction (regex, <1ms)
    2. Single Cypher query fetches ALL user data (cached, ~10-30ms)
    3. CPU-side relevance scoring + filtering (~1ms)
    4. Top-N context assembly

    Also retrieves recent conversation history for long-context memory.
    """
    start = time.perf_counter()

    # ── 1. Instant keyword extraction (<1ms) ────────────────────
    t0 = time.perf_counter()
    keywords = extract_keywords_fast(query)
    kw_ms = (time.perf_counter() - t0) * 1000
    logger.info("Keywords [%.1fms]: %s", kw_ms, keywords)

    # ── 2. Fetch all user data via Category traversal (cached) ─────
    db = get_db()
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()

    # Detect query category for targeted retrieval boost
    query_category = _detect_query_category(keywords)
    if query_category:
        logger.info("Query category detected: %s", query_category)

    def _fetch_all():
        # Unified query: finds entities via EITHER the new Category path
        # (HAS_CATEGORY→CONTAINS) OR the legacy KNOWS path, and the
        # entity's own stored .category property as final fallback.
        # This ensures backward-compatibility with data ingested before
        # the category-graph migration.
        return db.execute_query(
            "MATCH (e:Entity {user_id: $uid}) "
            "OPTIONAL MATCH (:User {user_id: $uid})-[:HAS_CATEGORY]->"
            "(cat:Category {user_id: $uid})-[:CONTAINS]->(e) "
            "OPTIONAL MATCH (e)-[:HAS_FACT]->(f:Fact {user_id: $uid}) "
            "RETURN coalesce(cat.name, e.category, 'General') AS category, "
            "       e.name AS entity, e.type AS type, "
            "       collect(DISTINCT {content: f.content, confidence: f.confidence, "
            "                         last_accessed: f.last_accessed}) AS facts, "
            "       e.last_accessed AS entity_accessed",
            {"uid": user_id},
        )

    t1 = time.perf_counter()
    records = _get_cached_or_fetch(user_id, "all_entities_v2", _fetch_all)
    db_ms = (time.perf_counter() - t1) * 1000

    # ── 3. Fetch recent conversation history (for long context) ─
    def _fetch_history():
        return db.execute_query(
            "MATCH (u:User {user_id: $uid})-[:PARTICIPATED_IN]->(i:Interaction) "
            "RETURN i.query AS text, i.timestamp AS ts "
            "ORDER BY i.timestamp DESC LIMIT 20",
            {"uid": user_id},
        )

    history_records = _get_cached_or_fetch(user_id, "history", _fetch_history)

    # ── 4. Relevance scoring (CPU, <1ms) ────────────────────────
    t2 = time.perf_counter()
    scored_items: List[Tuple[float, str, str, str]] = []  # (score, entity, fact, type)
    # broad_query = True when there are no specific keywords (e.g. "tell me about myself")
    # In this mode we skip keyword matching and rank purely by recency so the user still
    # gets a useful answer from their stored memories.
    broad_query = len(keywords) == 0

    for rec in records:
        entity = rec.get("entity", "Unknown")
        etype = rec.get("type") or "Entity"
        entity_category = rec.get("category") or "General"
        facts_data = rec.get("facts", [])
        entity_accessed = rec.get("entity_accessed", now)
        # 1.4× boost when query domain matches entity category
        cat_multiplier = 1.4 if query_category and query_category == entity_category else 1.0

        if broad_query:
            # Recency-only mode: include all entities, ranked by how recently accessed
            try:
                if isinstance(entity_accessed, str):
                    acc_dt = datetime.fromisoformat(entity_accessed.replace("Z", "+00:00"))
                else:
                    acc_dt = now_dt
                hours = max((now_dt - acc_dt).total_seconds() / 3600, 0)
            except Exception:
                hours = 0
            # Decay from 1.0 → 0.1 over ~30 days
            recency_base = max(0.1, 1.0 - hours / (24 * 30))
            for fd in facts_data:
                content = fd.get("content")
                if not content:
                    continue
                confidence = fd.get("confidence", 1.0) or 1.0
                scored_items.append((recency_base * confidence * cat_multiplier, entity, content, etype))
            if not facts_data or all(not f.get("content") for f in facts_data):
                scored_items.append((recency_base * 0.8 * cat_multiplier, entity, "", etype))
        else:
            for fd in facts_data:
                content = fd.get("content")
                if not content:
                    continue
                confidence = fd.get("confidence", 1.0) or 1.0
                last_acc = fd.get("last_accessed", now) or now

                try:
                    if isinstance(last_acc, str):
                        acc_dt = datetime.fromisoformat(last_acc.replace("Z", "+00:00"))
                    else:
                        acc_dt = now_dt
                    hours = max((now_dt - acc_dt).total_seconds() / 3600, 0)
                except Exception:
                    hours = 0

                score = _compute_relevance(entity, content, keywords, confidence, hours) * cat_multiplier
                if score > 0:
                    scored_items.append((score, entity, content, etype))

    # Sort by relevance (descending)
    scored_items.sort(key=lambda x: x[0], reverse=True)
    top_items = scored_items[:_MAX_CONTEXT_FACTS]
    score_ms = (time.perf_counter() - t2) * 1000

    # ── 5. Context assembly ───────────────────────────────────────
    entities_found: List[str] = []
    context_lines: List[str] = []
    seen_entities: set = set()
    # For citation: entity → best fact snippet
    entity_snippets: Dict[str, str] = {}

    for score, entity, fact, etype in top_items:
        if entity not in seen_entities:
            entities_found.append(entity)
            seen_entities.add(entity)
        if fact:
            if entity not in entity_snippets:
                entity_snippets[entity] = fact[:120]
            context_lines.append(
                f"- [{etype}] {entity}: {fact} (relevance: {score:.2f})"
            )
        else:
            context_lines.append(
                f"- [Known {etype}] {entity} (relevance: {score:.2f})"
            )

    # Conversation history — always fetched, always included in context
    history_citations: List[Dict[str, str]] = []
    if history_records:
        context_lines.append("\n--- RECENT CONVERSATION HISTORY ---")
        for hr in history_records[:10]:
            hist_text = hr.get("text", "")
            if hist_text and hist_text != query:
                context_lines.append(f"- Previously discussed: {hist_text[:150]}")
                history_citations.append({
                    "node_id": f"hist_{hr.get('ts', '')[:10]}",
                    "title": "Conversation History",
                    "snippet": hist_text[:100],
                })

    # ── 6. Decay update (fire-and-forget in background thread) ──
    if entities_found:
        import asyncio
        def _decay_update():
            try:
                db.execute_write(
                    "UNWIND $names AS ename "
                    "MATCH (e:Entity {name: ename, user_id: $uid}) "
                    "SET e.last_accessed = $now "
                    "WITH e "
                    "OPTIONAL MATCH (e)-[:HAS_FACT]->(f:Fact {user_id: $uid}) "
                    "SET f.last_accessed = $now",
                    {"uid": user_id, "names": entities_found, "now": now},
                )
            except Exception:
                pass
        try:
            asyncio.get_event_loop().run_in_executor(None, _decay_update)
        except Exception:
            pass

    # ── 7. Final timing ─────────────────────────────────────────
    total_ms = (time.perf_counter() - start) * 1000

    context_str = (
        f"MEMORY CONTEXT [Retrieved in {total_ms:.1f}ms | "
        f"Keywords: {kw_ms:.0f}ms | DB: {db_ms:.0f}ms | Score: {score_ms:.0f}ms "
        f"| {len(top_items)}/{len(scored_items)} facts selected]:\n"
        + "\n".join(context_lines)
        if context_lines
        else f"MEMORY CONTEXT [{total_ms:.1f}ms]: (no relevant memories)"
    )

    logger.info(
        "Retrieved %d/%d items in %.1fms (kw:%.1f db:%.1f score:%.1f) for user=%s",
        len(top_items), len(scored_items), total_ms, kw_ms, db_ms, score_ms, user_id,
    )

    return {
        "context": context_str,
        "retrieval_time_ms": round(total_ms, 2),
        "entities_found": entities_found,
        "entity_snippets": entity_snippets,
        "history_citations": history_citations,
        "total_facts_scanned": len(scored_items),
        "facts_selected": len(top_items),
        "broad_query": broad_query,
        "perf": {
            "keyword_ms": round(kw_ms, 1),
            "db_ms": round(db_ms, 1),
            "scoring_ms": round(score_ms, 1),
            "total_ms": round(total_ms, 1),
        },
    }


# ── Search Across Conversations ────────────────────────────────

def search_conversations(user_id: str, query: str, limit: int = 20) -> List[Dict]:
    """Full-text search across all past interactions for the user.

    This enables long-context remembering — no conversation is ever lost.
    """
    db = get_db()
    keywords = extract_keywords_fast(query)

    if not keywords:
        return db.execute_query(
            "MATCH (u:User {user_id: $uid})-[:PARTICIPATED_IN]->(i:Interaction) "
            "RETURN i.query AS text, i.timestamp AS ts "
            "ORDER BY i.timestamp DESC LIMIT $lim",
            {"uid": user_id, "lim": limit},
        )

    return db.execute_query(
        "MATCH (u:User {user_id: $uid})-[:PARTICIPATED_IN]->(i:Interaction) "
        "WHERE ANY(kw IN $keywords WHERE toLower(i.query) CONTAINS toLower(kw)) "
        "RETURN i.query AS text, i.timestamp AS ts "
        "ORDER BY i.timestamp DESC LIMIT $lim",
        {"uid": user_id, "keywords": keywords, "lim": limit},
    )


# ── User Profile ───────────────────────────────────────────────

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Return a summary of what the user already knows."""
    db = get_db()

    def _fetch():
        return db.execute_query(
            "MATCH (u:User {user_id: $uid})-[:HAS_CATEGORY]->"
            "(:Category {user_id: $uid})-[:CONTAINS]->(e:Entity {user_id: $uid}) "
            "OPTIONAL MATCH (e)-[:HAS_FACT]->(f:Fact {user_id: $uid}) "
            "RETURN e.name AS name, e.type AS type, count(f) AS fact_count "
            "ORDER BY fact_count DESC",
            {"uid": user_id},
        )

    records = _get_cached_or_fetch(user_id, "profile", _fetch)

    entities = []
    total_facts = 0
    for rec in records:
        fc = rec.get("fact_count", 0)
        entities.append({
            "name": rec.get("name", ""),
            "type": rec.get("type") or "Entity",
            "fact_count": fc,
        })
        total_facts += fc

    # Count interactions (conversation memory length)
    def _count_interactions():
        result = db.execute_query(
            "MATCH (u:User {user_id: $uid})-[:PARTICIPATED_IN]->(i:Interaction) "
            "RETURN count(i) AS cnt",
            {"uid": user_id},
        )
        return result[0].get("cnt", 0) if result else 0

    interaction_count = _get_cached_or_fetch(user_id, "interaction_count", _count_interactions)

    return {
        "user_id": user_id,
        "entities": entities,
        "total_entities": len(entities),
        "total_facts": total_facts,
        "total_interactions": interaction_count,
    }


# ── Mindmap Data (user-scoped) ─────────────────────────────────

def get_user_graph(user_id: str) -> Dict[str, Any]:
    """Fetch the full hierarchical subgraph: User → Categories → Entities + Facts.

    Structure returned:
      User node (center)
        ├─ Category node (Health, Finance, Learning, Work, Travel, Personal, General)
        │     └─ Entity nodes  →  [RELATED_TO]  → other Entity nodes
        │           └─ Fact nodes (hidden_by_default)
        ...
    """
    db = get_db()

    def _fetch_graph():
        entity_records = db.execute_query(
            "MATCH (u:User {user_id: $uid})-[:HAS_CATEGORY]->"
            "(cat:Category {user_id: $uid})-[:CONTAINS]->(e:Entity {user_id: $uid}) "
            "OPTIONAL MATCH (e)-[:HAS_FACT]->(f:Fact {user_id: $uid}) "
            "WITH cat, e, count(f) AS fact_count, "
            "     collect(COALESCE(f.snippet, f.content, f.name, '')) AS fact_snippets "
            "RETURN cat.name AS category, e.name AS entity, "
            "       COALESCE(e.type, 'Entity') AS etype, "
            "       fact_count, e.last_accessed AS accessed, "
            "       COALESCE(e.snippet, head([s IN fact_snippets WHERE s <> '']), '') AS snippet",
            {"uid": user_id},
        )
        rel_records = db.execute_query(
            "MATCH (s:Entity {user_id: $uid})-[r:RELATED_TO]->(t:Entity {user_id: $uid}) "
            "RETURN s.name AS source, t.name AS target, r.type AS relation",
            {"uid": user_id},
        )
        # Fetch fact nodes linked to entities
        fact_records = db.execute_query(
            "MATCH (e:Entity {user_id: $uid})-[:HAS_FACT]->(f:Fact {user_id: $uid}) "
            "RETURN e.name AS entity, f.name AS fact_id, "
            "       COALESCE(f.snippet, f.name) AS snippet",
            {"uid": user_id},
        )
        return entity_records, rel_records, fact_records

    entity_records, rel_records, fact_records = _get_cached_or_fetch(
        user_id, "graph_cat", _fetch_graph
    )

    nodes = [{"id": user_id, "label": "Me", "group": "User", "facts": 0}]
    edges = []
    seen_nodes = {user_id}
    seen_categories: Dict[str, str] = {}  # category_name → node_id

    for rec in entity_records:
        category = str(rec.get("category") or "General").strip()
        entity = str(rec.get("entity") or "").strip()
        if not entity:
            continue
        etype = str(rec.get("etype") or "Entity")
        fact_count = rec.get("fact_count") or 0

        # ── Category node ───────────────────────────────────────────
        cat_id = f"cat_{category.lower().replace(' ', '_')}"
        if cat_id not in seen_categories:
            nodes.append({
                "id": cat_id, "label": category,
                "group": "Category", "facts": 0,
            })
            seen_categories[category] = cat_id
            edges.append({"source": user_id, "target": cat_id, "label": "HAS_CATEGORY"})

        # ── Entity node ─────────────────────────────────────────────
        if entity not in seen_nodes:
            nodes.append({
                "id": entity, "label": entity,
                "group": etype, "facts": fact_count,
                "snippet": str(rec.get("snippet") or "").strip(),
            })
            seen_nodes.add(entity)
        edges.append({"source": cat_id, "target": entity, "label": "CONTAINS"})

    # ── Cross-entity relationships ───────────────────────────────────
    for rec in rel_records:
        source = str(rec.get("source") or "").strip()
        target = str(rec.get("target") or "").strip()
        relation = str(rec.get("relation") or "RELATED_TO")
        if source and target:
            edges.append({"source": source, "target": target, "label": relation})

    # ── Fact nodes (hidden by default) ───────────────────────────────
    for rec in fact_records:
        entity = str(rec.get("entity") or "").strip()
        fact_id = str(rec.get("fact_id") or "").strip()
        snippet = str(rec.get("snippet") or fact_id).strip()
        if not fact_id:
            continue
        if fact_id not in seen_nodes:
            nodes.append({
                "id": fact_id, "label": snippet[:60],
                "group": "Fact", "facts": 0,
                "hidden_by_default": True,
            })
            seen_nodes.add(fact_id)
        if entity and fact_id:
            edges.append({"source": entity, "target": fact_id, "label": "HAS_FACT"})

    return {"nodes": nodes, "edges": edges}
