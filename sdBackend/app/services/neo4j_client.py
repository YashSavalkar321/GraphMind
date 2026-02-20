"""
GraphMind — Neo4j async driver wrapper.
All queries enforce user isolation via user_id.
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

        # Create indexes for performance
        await self._ensure_indexes()

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j connection closed")

    async def _ensure_indexes(self) -> None:
        """Create indexes for fast lookups."""
        async with self._driver.session() as session:
            for label in ("Entity", "Concept", "Document", "Fact"):
                await session.run(
                    f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.id)"
                )
                await session.run(
                    f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.user_id)"
                )
        logger.info("Neo4j indexes ensured")

    # ────────────────────────────────────────────────────────────
    #  Write Operations
    # ────────────────────────────────────────────────────────────

    async def create_node(
        self,
        user_id: str,
        name: str,
        node_type: str,
        description: str = "",
        source: str = "",
    ) -> str:
        """Create a node with the appropriate label. Returns the node id."""
        node_id = f"n_{uuid.uuid4().hex[:12]}"
        label = node_type.capitalize()  # concept → Concept
        if label not in ("Entity", "Concept", "Document", "Fact"):
            label = "Concept"

        query = f"""
        CREATE (n:{label} {{
            id: $id,
            user_id: $user_id,
            name: $name,
            description: $description,
            source: $source,
            timestamp: datetime()
        }})
        RETURN n.id AS id
        """
        async with self._driver.session() as session:
            result = await session.run(
                query,
                id=node_id,
                user_id=user_id,
                name=name,
                description=description,
                source=source,
            )
            record = await result.single()
            return record["id"]

    async def create_edge(
        self,
        user_id: str,
        source_id: str,
        target_id: str,
        rel_type: str = "RELATES_TO",
        weight: float = 1.0,
    ) -> Optional[str]:
        """Create a relationship between two nodes (same user)."""
        edge_id = f"e_{uuid.uuid4().hex[:8]}"
        # Sanitize relationship type
        rel = rel_type.upper().replace(" ", "_")
        if rel not in ("USES", "RELATES_TO", "INCLUDES", "CONTRADICTS"):
            rel = "RELATES_TO"

        query = f"""
        MATCH (a {{id: $source_id, user_id: $user_id}})
        MATCH (b {{id: $target_id, user_id: $user_id}})
        CREATE (a)-[r:{rel} {{id: $edge_id, weight: $weight, last_accessed: datetime()}}]->(b)
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

    # ────────────────────────────────────────────────────────────
    #  Read — Mindmap
    # ────────────────────────────────────────────────────────────

    async def get_all_nodes(self, user_id: str) -> List[Dict[str, Any]]:
        """Return every node for a user."""
        query = """
        MATCH (n)
        WHERE n.user_id = $user_id
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
        """Return every edge for a user's nodes."""
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.user_id = $user_id AND b.user_id = $user_id
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
          AND toLower(center.name) CONTAINS toLower($entity_name)
        WITH center LIMIT 1
        MATCH path = (center)-[*1..%d]-(neighbor)
        WHERE neighbor.user_id = $user_id AND neighbor <> center
        WITH neighbor, relationships(path)[0] AS rel
        RETURN DISTINCT neighbor.id AS id,
               neighbor.name AS name,
               neighbor.description AS description,
               labels(neighbor)[0] AS node_type,
               type(rel) AS relation
        UNION
        MATCH (center)
        WHERE center.user_id = $user_id
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
        """Find an existing node by name (exact, case-insensitive)."""
        query = """
        MATCH (n)
        WHERE n.user_id = $user_id AND toLower(n.name) = toLower($name)
        RETURN n.id AS id, n.name AS name, labels(n)[0] AS label_type
        LIMIT 1
        """
        async with self._driver.session() as session:
            result = await session.run(query, user_id=user_id, name=name)
            record = await result.single()
            return dict(record) if record else None


# Singleton
neo4j_client = Neo4jClient()
