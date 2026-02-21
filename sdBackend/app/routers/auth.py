"""
GraphMind — Auth Router
POST /auth/signup  → register user, create JWT, create root User node in Neo4j
POST /auth/login   → verify credentials, return JWT
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.models import SignupRequest, SignupResponse, LoginRequest, LoginResponse
from app.services.auth import hash_password, verify_password, create_access_token
from app.services.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── In-memory user store (swap for a real DB table in production) ──
# Schema: { email: { user_id, name, email, hashed_password } }
_user_store: dict = {}


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(req: SignupRequest):
    """
    1. Validate uniqueness
    2. Hash password
    3. Create root User node in Neo4j via MERGE
    4. Issue JWT
    """
    if req.email.lower() in _user_store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    hashed = hash_password(req.password)

    # Persist to in-memory store
    _user_store[req.email.lower()] = {
        "user_id": user_id,
        "name": req.name,
        "email": req.email.lower(),
        "hashed_password": hashed,
    }

    # ── Create root User node in Neo4j ──
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        await neo4j_client.create_user_node(
            user_id=user_id, name=req.name, timestamp=timestamp
        )
        logger.info("Created root User node for %s (%s)", req.name, user_id)
    except Exception as e:
        logger.error("Failed to create User node in Neo4j: %s", e)
        # Don't block signup — the node can be created lazily later

    token = create_access_token(user_id=user_id, name=req.name)

    return SignupResponse(
        user_id=user_id,
        name=req.name,
        email=req.email.lower(),
        token=token,
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Verify credentials and return a JWT."""
    user = _user_store.get(req.email.lower())
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=user["user_id"], name=user["name"])

    return LoginResponse(
        user_id=user["user_id"],
        name=user["name"],
        email=user["email"],
        token=token,
    )
