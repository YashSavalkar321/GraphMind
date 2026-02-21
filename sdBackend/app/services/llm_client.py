"""
GraphMind — LLM client (Ollama / Groq / Gemini).
Strict JSON extraction + chat generation. NO LangChain.

Environment example (put in .env):
LLM_PROVIDER=groq
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=graphmind_chunks
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=info
"""

import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Timeouts ──
_TIMEOUT = httpx.Timeout(120.0, connect=10.0)  # Ollama local inference can be slower


# ═══════════════════════════════════════════════════════════
#  Generic call dispatcher
# ═══════════════════════════════════════════════════════════

async def llm_generate(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Route to the configured LLM provider and return raw text."""
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        return await _call_ollama(system_prompt, user_prompt, temperature, max_tokens)
    elif provider == "groq":
        return await _call_groq(system_prompt, user_prompt, temperature, max_tokens)
    elif provider == "gemini":
        return await _call_gemini(system_prompt, user_prompt, temperature, max_tokens)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


# ═══════════════════════════════════════════════════════════
#  Ollama (local llama3.1 — no API key required)
# ═══════════════════════════════════════════════════════════

async def _call_ollama(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


# ═══════════════════════════════════════════════════════════
#  Groq (Llama 3 70B)
# ═══════════════════════════════════════════════════════════

async def _call_groq(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ═══════════════════════════════════════════════════════════
#  Google Gemini
# ═══════════════════════════════════════════════════════════

async def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response is not None else "<no body>"
            logger.error(
                "LLM request failed: status=%s url=%s body=%s",
                e.response.status_code if e.response else "<no status>",
                url,
                body,
            )
            raise
        except httpx.RequestError as e:
            logger.error("LLM request error: %s", str(e))
            raise
        data = resp.json()
        # Google Gemini returns candidates -> content -> parts -> text
        return data["candidates"][0]["content"]["parts"][0]["text"]


# ═══════════════════════════════════════════════════════════
#  JSON extraction helper
# ═══════════════════════════════════════════════════

def parse_json_from_llm(raw: str) -> Optional[Dict[str, Any]]:
    """
    Extract a JSON object from potentially markdown-wrapped LLM output.
    Handles ```json ... ``` wrappers and leading/trailing noise.
    """
    # Try to extract from code fences first
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Find first { ... last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse JSON from LLM output: %s", raw[:200])
    return None