"""
GraphMind — Neo4j Connection Manager
======================================
Singleton-style driver management, schema constraints, and generic
Cypher query execution helpers.

Member 1 (DB Lead) deliverables:
- Composite constraints for user isolation
- UUID memory_id on all nodes
- Memory decay indexes
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver, Result

# ── Load environment variables ──────────────────────────────────
# override=True ensures .env values always win over stale system env vars
load_dotenv(override=True)

logger = logging.getLogger("graphmind.database")


class Neo4jConnection:
    """Manages the lifecycle of a single Neo4j driver instance."""

    _instance: Optional["Neo4jConnection"] = None
    _driver: Optional[Driver] = None

    # ── Singleton accessor ──────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "Neo4jConnection":
        """Return (or create) the global Neo4jConnection singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Driver lifecycle ────────────────────────────────────────

    def init_driver(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Initialise the Neo4j driver from explicit args or env vars."""
        uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = user or os.getenv("NEO4J_USER", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD", "")

        if self._driver is not None:
            logger.info("Driver already initialised — closing existing driver first.")
            self.close_driver()

        logger.info("Connecting to Neo4j at %s …", uri)
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close_driver(self) -> None:
        """Gracefully close the Neo4j driver."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed.")

    def verify_connectivity(self) -> bool:
        """Ping Neo4j to ensure the connection is live."""
        if self._driver is None:
            raise RuntimeError("Driver not initialised. Call init_driver() first.")
        try:
            self._driver.verify_connectivity()
            logger.info("Neo4j connectivity verified ✓")
            return True
        except Exception as exc:
            logger.error("Neo4j connectivity check failed: %s", exc)
            return False

    # ── Schema / constraints (Member 1: DB Lead) ────────────────

    def setup_constraints(self) -> None:
        """Create uniqueness constraints and indexes.

        Constraints
        -----------
        * User.user_id — unique (no duplicate users)
        * Entity (name + user_id) — composite uniqueness (user isolation)

        Indexes
        -------
        * Entity.name — for fast keyword lookups
        * Fact.last_accessed — for memory decay ordering
        * Interaction.timestamp — for chronological queries
        """
        if self._driver is None:
            raise RuntimeError("Driver not initialised. Call init_driver() first.")

        # Drop old composite constraint that conflicts with MERGE pattern
        drop_statements = [
            "DROP CONSTRAINT constraint_entity_composite IF EXISTS",
        ]

        statements = [
            # Uniqueness constraints
            (
                "constraint_user_id_unique",
                "CREATE CONSTRAINT constraint_user_id_unique IF NOT EXISTS "
                "FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            ),
            # Composite index for Entity (name + user_id) — range index, NOT unique
            (
                "index_entity_name_user",
                "CREATE INDEX index_entity_name_user IF NOT EXISTS "
                "FOR (e:Entity) ON (e.name, e.user_id)",
            ),
            # Individual indexes for performance
            (
                "index_entity_name",
                "CREATE INDEX index_entity_name IF NOT EXISTS "
                "FOR (e:Entity) ON (e.name)",
            ),
            (
                "index_entity_user",
                "CREATE INDEX index_entity_user IF NOT EXISTS "
                "FOR (e:Entity) ON (e.user_id)",
            ),
            (
                "index_fact_accessed",
                "CREATE INDEX index_fact_accessed IF NOT EXISTS "
                "FOR (f:Fact) ON (f.last_accessed)",
            ),
            (
                "index_fact_user",
                "CREATE INDEX index_fact_user IF NOT EXISTS "
                "FOR (f:Fact) ON (f.user_id)",
            ),
            (
                "index_interaction_ts",
                "CREATE INDEX index_interaction_ts IF NOT EXISTS "
                "FOR (i:Interaction) ON (i.timestamp)",
            ),
            (
                "index_interaction_user_ts",
                "CREATE INDEX index_interaction_user_ts IF NOT EXISTS "
                "FOR (i:Interaction) ON (i.user_id, i.timestamp)",
            ),
            (
                "index_category_user",
                "CREATE INDEX index_category_user IF NOT EXISTS "
                "FOR (c:Category) ON (c.user_id, c.name)",
            ),
            (
                "index_chatsession_user",
                "CREATE INDEX index_chatsession_user IF NOT EXISTS "
                "FOR (cs:ChatSession) ON (cs.user_id)",
            ),
            (
                "constraint_chatsession_id",
                "CREATE CONSTRAINT constraint_chatsession_id IF NOT EXISTS "
                "FOR (cs:ChatSession) REQUIRE cs.chat_id IS UNIQUE",
            ),
        ]

        with self._driver.session() as session:
            # Drop old constraints first
            for drop_cypher in drop_statements:
                try:
                    session.run(drop_cypher)
                except Exception:
                    pass  # Ignore if doesn't exist

            for name, cypher in statements:
                try:
                    session.run(cypher)
                    logger.info("Schema '%s' ensured.", name)
                except Exception as exc:
                    logger.warning("Could not create '%s': %s", name, exc)

    # ── Generic query helpers ───────────────────────────────────

    def execute_query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run a **read** Cypher query and return records as dicts."""
        if self._driver is None:
            raise RuntimeError("Driver not initialised. Call init_driver() first.")

        parameters = parameters or {}

        with self._driver.session(database=database) as session:
            result: Result = session.run(cypher, parameters)
            return [record.data() for record in result]

    def execute_write(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run a **write** Cypher query inside an explicit write transaction."""
        if self._driver is None:
            raise RuntimeError("Driver not initialised. Call init_driver() first.")

        parameters = parameters or {}

        def _tx_fn(tx):
            result = tx.run(cypher, parameters)
            return [record.data() for record in result]

        with self._driver.session(database=database) as session:
            return session.execute_write(_tx_fn)


# ── Module-level convenience ────────────────────────────────────

def get_db() -> Neo4jConnection:
    """FastAPI-friendly dependency that returns the singleton connection."""
    return Neo4jConnection.get_instance()
