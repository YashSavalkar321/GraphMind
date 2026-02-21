"""
GraphMind — Neo4j async driver wrapper.
All queries enforce user isolation via user_id.
Entity resolution uses MERGE + toLower() normalization.
Startup ensures uniqueness constraints and indexes for <100ms reads.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings

logger = logging.getLogger(__name__)

# ── Color palette per node type (matches frontend COLOR_MAP) ──
NODE_COLORS = {
    "concept": "#6366f1",
    "entity": "#8b5cf6",
    "document": "#0ea5e9",
    "fact": "#10b981",
}


class Neo4jClient:
    """Thin async wrapper around the Neo4j Python driver."""

    def __init__(self) -> None:
        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        # Verify connectivity
        async with self._driver.session() as session:
            await session.run("RETURN 1")
        logger.info("Neo4j connected at %s", settings.neo4j_uri)

        # Create constraints & indexes for performance
        await self._ensure_indexes()

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j connection closed")

    # ────────────────────────────────────────────────────────
    #  Startup: Constraints & Indexes
    # ────────────────────────────────────────────────────────

    async def _ensure_indexes(self) -> None:
        """
        Create uniqueness constraints and composite indexes on startup.
        These are idempotent (IF NOT EXISTS) and guarantee <100ms lookups.
        """
        async with self._driver.session() as session:
            # 1. Uniqueness constraint on User.user_id
            await session.run(
                "CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (n:User) REQUIRE n.user_id IS UNIQUE"
            )

            # 2. Index on Entity.user_id for user-scoped queries
            await session.run(
                "CREATE INDEX entity_user_idx IF NOT EXISTS "
                "FOR (n:Entity) ON (n.user_id)"
            )

            # 3. Index on Concept.user_id for user-scoped queries
            await session.run(
                "CREATE INDEX concept_user_idx IF NOT EXISTS "
                "FOR (n:Concept) ON (n.user_id)"
            )

            # 4. Additional indexes for Document and Fact labels
            await session.run(
                "CREATE INDEX document_user_idx IF NOT EXISTS "
                "FOR (n:Document) ON (n.user_id)"
            )
            await session.run(
                "CREATE INDEX fact_user_idx IF NOT EXISTS "
                "FOR (n:Fact) ON (n.user_id)"
            )

            # 5. Composite indexes on (user_id, name_lower) for fast MERGE
            for label in ("Entity", "Concept", "Document", "Fact"):
                await session.run(
                    f"CREATE INDEX {label.lower()}_name_idx IF NOT EXISTS "
                    f"FOR (n:{label}) ON (n.user_id, n.name_lower)"
                )

        logger.info("Neo4j constraints & indexes ensured")

    # ────────────────────────────────────────────────────────
    #  User Node (root node per user)
    # ────────────────────────────────────────────────────────

    async def create_user_node(
        self, user_id: str, name: str, timestamp: str
    ) -> None:
        """
        Create the root User node on signup.
        Uses MERGE to be idempotent.
        """
        query = """
        MERGE (u:User {user_id: $user_id})
        ON CREATE SET u.name      = $name,
                      u.created_at = $timestamp
        ON MATCH SET  u.name      = $name
        """
        async with self._driver.session() as session:
            await session.run(
                query, user_id=user_id, name=name, timestamp=timestamp
            )

    # ────────────────────────────────────────────────────────
    #  Write — Entity-Resolved Node Creation (MERGE)
    # ────────────────────────────────────────────────────────

    async def merge_node(
        self,
        user_id: str,
        name: str,
        node_type: str,
        description: str = "",
        source: str = "",
    ) -> str:
        """
        MERGE a node using toLower(name) normalization.
        If an existing node matches (user_id + name_lower), reuse it;
        otherwise create a new one.  Returns the node id.
        Also links the node to the root User node via [:OWNS_MEMORY].
        """
        label = node_type.capitalize()
        if label not in ("Entity", "Concept", "Document", "Fact"):
            label = "Concept"
        new_id = f"n_{uuid.uuid4().hex[:12]}"
        name_lower = name.strip().lower()

        # MERGE on (user_id, name_lower) guarantees dedup
        query = f"""
        MERGE (n:{label} {{user_id: $user_id, name_lower: $name_lower}})
        ON CREATE SET n.id          = $new_id,
                      n.name        = $name,
                      n.description = $description,
                      n.source      = $source,
                      n.timestamp   = datetime()
        ON MATCH SET  n.description = CASE
                          WHEN size(n.description) < size($description)
                          THEN $description ELSE n.description END,
                      n.source      = CASE
                          WHEN n.source = '' THEN $source ELSE n.source END
        WITH n
        MERGE (u:User {{user_id: $user_id}})
        MERGE (u)-[:OWNS_MEMORY]->(n)
        RETURN n.id AS id
        """
        async with self._driver.session() as session:
            result = await session.run(
                query,
                user_id=user_id,
                name_lower=name_lower,
                new_id=new_id,
                name=name.strip(),
                description=description,
                source=source,
            )
            record = await result.single()
            return record["id"] if record else new_id

    async def create_edge(
        self,
        user_id: str,
        source_id: str,
        target_id: str,
        rel_type: str = "RELATES_TO",
        weight: float = 1.0,
    ) -> Optional[str]:
        """Create a relationship between two nodes (same user).
        Uses MERGE to avoid duplicate edges."""
        edge_id = f"e_{uuid.uuid4().hex[:8]}"
        rel = rel_type.upper().replace(" ", "_")
        if rel not in (
            "USES", "RELATES_TO", "INCLUDES", "CONTRADICTS",
            "CAUSES", "ENABLES", "REQUIRES", "IMPLEMENTS", "OWNS_MEMORY",
        ):
            rel = "RELATES_TO"

        query = f"""
        MATCH (a {{id: $source_id, user_id: $user_id}})
        MATCH (b {{id: $target_id, user_id: $user_id}})
        MERGE (a)-[r:{rel}]->(b)
        ON CREATE SET r.id            = $edge_id,
                      r.weight        = $weight,
                      r.last_accessed = datetime()
        ON MATCH SET  r.weight        = r.weight + $weight,
                      r.last_accessed = datetime()
        RETURN r.id AS id
        """
        async with self._driver.session() as session:
            result = await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                user_id=user_id,
                edge_id=edge_id,
                weight=weight,
            )
            record = await result.single()
            return record["id"] if record else None

    # ── Legacy create_node (delegates to merge_node) ──
    async def create_node(
        self,
        user_id: str,
        name: str,
        node_type: str,
        description: str = "",
        source: str = "",
    ) -> str:
        """Backward-compatible alias — delegates to merge_node."""
        return await self.merge_node(
            user_id=user_id,
            name=name,
            node_type=node_type,
            description=description,
            source=source,
        )

    # ────────────────────────────────────────────────────────────
    #  Read — Mindmap
    # ────────────────────────────────────────────────────────────

    async def get_all_nodes(self, user_id: str) -> List[Dict[str, Any]]:
        """Return every node for a user (excluding the root User node)."""
        query = """
        MATCH (n)
        WHERE n.user_id = $user_id AND (n:Entity OR n:Concept OR n:Document OR n:Fact)
        RETURN n.id AS id,
               labels(n)[0] AS label_type,
               n.name AS name,
               n.description AS description,
               n.source AS source
        """
        results = []
        async with self._driver.session() as session:
            cursor = await session.run(query, user_id=user_id)
            async for record in cursor:
                results.append(dict(record))
        return results

    async def get_all_edges(self, user_id: str) -> List[Dict[str, Any]]:
        """Return every edge for a user's nodes (excluding OWNS_MEMORY)."""
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.user_id = $user_id AND b.user_id = $user_id
          AND (a:Entity OR a:Concept OR a:Document OR a:Fact)
          AND (b:Entity OR b:Concept OR b:Document OR b:Fact)
        RETURN r.id AS id,
               a.id AS source,
               b.id AS target,
               type(r) AS rel_type
        """
        results = []
        async with self._driver.session() as session:
            cursor = await session.run(query, user_id=user_id)
            async for record in cursor:
                results.append(dict(record))
        return results

    # ────────────────────────────────────────────────────────────
    #  Read — Retrieval (1-hop neighborhood)
    # ────────────────────────────────────────────────────────────

    async def get_neighborhood(
        self, user_id: str, entity_name: str, hops: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Find a node by name (case-insensitive) and return its n-hop neighborhood.
        Returns a list of {id, name, description, node_type, relation} dicts.
        """
        query = """
        MATCH (center)
        WHERE center.user_id = $user_id 
          AND (center:Entity OR center:Concept OR center:Document OR center:Fact)
          AND toLower(center.name) CONTAINS toLower($entity_name)
        WITH center LIMIT 1
        MATCH path = (center)-[*1..%d]-(neighbor)
        WHERE neighbor.user_id = $user_id AND neighbor <> center 
          AND (neighbor:Entity OR neighbor:Concept OR neighbor:Document OR neighbor:Fact)
        WITH neighbor, relationships(path)[0] AS rel
        RETURN DISTINCT neighbor.id AS id,
               neighbor.name AS name,
               neighbor.description AS description,
               labels(neighbor)[0] AS node_type,
               type(rel) AS relation
        UNION
        MATCH (center)
        WHERE center.user_id = $user_id 
          AND (center:Entity OR center:Concept OR center:Document OR center:Fact)
          AND toLower(center.name) CONTAINS toLower($entity_name)
        RETURN center.id AS id,
               center.name AS name,
               center.description AS description,
               labels(center)[0] AS node_type,
               'CENTER' AS relation
        LIMIT 1
        """ % hops

        results = []
        async with self._driver.session() as session:
            try:
                cursor = await session.run(
                    query, user_id=user_id, entity_name=entity_name
                )
                async for record in cursor:
                    results.append(dict(record))
            except Exception as e:
                logger.warning("Neighborhood query failed: %s — falling back", e)
                # Simpler fallback query
                fallback = """
                MATCH (n)
                WHERE n.user_id = $user_id
                  AND (n:Entity OR n:Concept OR n:Document OR n:Fact)
                  AND toLower(n.name) CONTAINS toLower($entity_name)
                RETURN n.id AS id,
                       n.name AS name,
                       n.description AS description,
                       labels(n)[0] AS node_type,
                       'MATCH' AS relation
                LIMIT 5
                """
                cursor = await session.run(
                    fallback, user_id=user_id, entity_name=entity_name
                )
                async for record in cursor:
                    results.append(dict(record))
        return results

    async def find_node_by_name(
        self, user_id: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Find an existing node by name (exact, case-insensitive) using indexed name_lower."""
        query = """
        MATCH (n)
        WHERE n.user_id = $user_id 
          AND (n:Entity OR n:Concept OR n:Document OR n:Fact)
          AND n.name_lower = $name_lower
        RETURN n.id AS id, n.name AS name, labels(n)[0] AS label_type
        LIMIT 1
        """
        async with self._driver.session() as session:
            result = await session.run(
                query, user_id=user_id, name_lower=name.strip().lower()
            )
            record = await result.single()
            return dict(record) if record else None


# Singleton
neo4j_client = Neo4jClient()
