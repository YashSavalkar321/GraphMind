"""
GraphMind — Clerk Authentication
==================================
JWT verification using Clerk for FastAPI endpoints.
Provides ``get_current_user`` dependency that extracts user_id from JWT.

Supports two modes:
1. **Dev mode** (X-User-Id header): When no Bearer token is provided,
   falls back to X-User-Id header. This allows the Streamlit frontend
   to authenticate without requiring Clerk JS SDK.
2. **Production mode** (Clerk JWT): When a Bearer token is provided,
   validates it against Clerk's JWKS endpoint.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv(override=True)

logger = logging.getLogger("graphmind.auth")

# ── Configuration ──────────────────────────────────────────────

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")

# ── Own HS256 JWT configuration (used by /auth/signup + /auth/login) ──
JWT_SECRET = os.getenv("JWT_SECRET", "graphmind-change-me-in-prod")
JWT_ALGORITHM = "HS256"

_PLACEHOLDERS = {"", "sk_test_your_key_here", "pk_test_your_key_here"}

_clerk_configured = (
    CLERK_SECRET_KEY not in _PLACEHOLDERS
    and CLERK_PUBLISHABLE_KEY not in _PLACEHOLDERS
)

# Derive JWKS URL from publishable key if not set
if _clerk_configured and not CLERK_JWKS_URL:
    domain = CLERK_PUBLISHABLE_KEY.replace("pk_test_", "").replace("pk_live_", "")
    CLERK_JWKS_URL = f"https://{domain}/.well-known/jwks.json"


# ── Security scheme ────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency: extract user_id from JWT or X-User-Id header.

    Auth priority:
    1. Own HS256 Bearer JWT (issued by /auth/signup or /auth/login)
    2. Clerk RS256 Bearer JWT (verified via Clerk JWKS)
    3. X-User-Id header (for dev mode)
    4. user_id query parameter (for GET endpoints)
    5. 401 Unauthorized

    Returns
    -------
    str
        The authenticated user's ID.
    """
    # ── Option 1: Own HS256 JWT (issued by this backend) ───────────
    if credentials is not None:
        token = credentials.credentials
        try:
            import jwt as pyjwt
            payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                logger.info("HS256 authenticated user: %s", user_id)
                return user_id
        except Exception:
            # Not a valid HS256 token — try Clerk RS256 next
            pass

    # ── Option 2: Bearer JWT token (Clerk RS256) ───────────────
    jwt_failed = False
    if credentials is not None and _clerk_configured:
        token = credentials.credentials
        try:
            import jwt
            from jwt import PyJWKClient

            jwks_client = PyJWKClient(CLERK_JWKS_URL, cache_keys=True)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )

            user_id = payload.get("sub")
            if not user_id:
                logger.warning("JWT token has no 'sub' claim, falling back")
                jwt_failed = True
            else:
                logger.info("JWT authenticated user: %s", user_id)
                return user_id

        except Exception as e:
            # JWT failed — fall through to X-User-Id header
            logger.warning("JWT validation failed (%s), falling back to header auth", e)
            jwt_failed = True

    # ── Option 2: X-User-Id header (dev mode / fallback) ───────
    user_id_header = request.headers.get("X-User-Id")
    if user_id_header:
        logger.info("Header authenticated user: %s", user_id_header)
        return user_id_header

    # ── Option 3: query param (for GET endpoints) ──────────────
    user_id_param = request.query_params.get("user_id")
    if user_id_param:
        logger.info("Query param authenticated user: %s", user_id_param)
        return user_id_param

    # ── No auth found ──────────────────────────────────────────
    raise HTTPException(
        status_code=401,
        detail="Missing authentication. Provide X-User-Id header or Bearer token.",
    )
