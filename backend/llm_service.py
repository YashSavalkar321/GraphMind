"""
GraphMind — LLM Service
=========================
Thin wrapper around Groq / Google Gemini chat-completion APIs.
Handles knowledge extraction, answer generation, keyword extraction,
and learning roadmap generation.

No pre-built memory libraries are used — all prompting is manual.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Generator, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("graphmind.llm")

# ── Client initialisation ──────────────────────────────────────

_groq_client = None
_gemini_client = None


def _get_groq_client():
    """Lazy-init the Groq client."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if api_key and not api_key.startswith("gsk_your"):
            from groq import Groq
            _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_gemini_client():
    """Lazy-init the Google Gemini client (google-genai SDK)."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key and api_key != "your_gemini_api_key_here":
            from google import genai
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _chat(system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
    """Send a chat completion request. Tries Groq first, then Gemini."""
    model = model or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    # ── Try Groq ────────────────────────────────────────────────
    groq = _get_groq_client()
    if groq is not None:
        try:
            resp = groq.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("Groq call failed, falling back to Gemini: %s", exc)

    # ── Try Gemini ──────────────────────────────────────────────
    gemini = _get_gemini_client()
    if gemini is not None:
        try:
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            resp = gemini.models.generate_content(
                model=gemini_model,
                contents=f"{system_prompt}\n\n---\n\n{user_prompt}",
            )
            return resp.text.strip()
        except Exception as exc:
            logger.error("Gemini call also failed: %s", exc)

    raise RuntimeError(
        "No LLM provider available. "
        "Set GROQ_API_KEY or GEMINI_API_KEY in your .env file."
    )


# ── JSON parser helper ─────────────────────────────────────────

def _parse_json_from_llm(raw: str) -> dict:
    """Robustly parse JSON from an LLM response."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.error("Could not parse LLM output as JSON:\n%s", raw)
    return {"entities": [], "relationships": [], "facts": []}


# ── Knowledge Extraction ──────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """\
You are a Knowledge Graph Extractor. Analyze the user's text and output
a valid JSON object with exactly these three keys:

1. "entities": a list of objects, each with:
   - "name" (string)
   - "type" (string, e.g. "Technology", "Person", "Place", "Concept",
     "Skill", "Topic", "Resource", "Goal", "Symptom", "Medication",
     "Expense", "Destination")
   - "category" (string — one of: "Health", "Finance", "Learning",
     "Work", "Travel", "Personal", "General")
2. "relationships": a list of objects, each with "source" (string),
   "relation" (string, e.g. "LEARNING", "WORKS_AT", "LIKES",
   "PREREQUISITE_OF", "LEADS_TO", "RESOURCE_FOR", "WEAK_AT",
   "STRONG_AT", "INTERESTED_IN"), and "target" (string).
3. "facts": a list of objects, each with "content" (string — a distinct
   factual statement) and "entity_name" (string — the entity this fact
   is about).

Category assignment rules:
- Health : symptoms, medications, conditions, triggers, health habits, diet, sleep, exercise
- Finance : budgets, expenses, income, savings, investments, financial goals, debts
- Learning: skills, topics, courses, study plans, prerequisites, learning resources
- Work    : projects, code, engineering tasks, team standards, tools, PR reviews, deadlines
- Travel  : destinations, trips, hotels, flights, itineraries, travel preferences
- Personal: hobbies, personal preferences, relationships, habits, life events
- General : anything that does not fit the above categories

Other rules:
- Extract ALL meaningful entities, even implicit ones.
- Every fact must reference an entity by name.
- Use UPPER_SNAKE_CASE for relation names.
- If the text is a QUESTION or QUERY (e.g. "what is my weakness?",
  "tell me about X"), return EMPTY arrays for all three keys:
  {"entities": [], "relationships": [], "facts": []}
  Questions are NOT factual statements — do NOT create entities from them.
- Only extract from DECLARATIVE statements.
- Output ONLY the JSON object — no markdown, no explanation.
"""


async def extract_knowledge(text: str) -> dict:
    """Use the LLM to extract entities, relationships, and facts."""
    raw = await asyncio.to_thread(_chat, EXTRACTION_SYSTEM_PROMPT, text)
    parsed = _parse_json_from_llm(raw)
    parsed.setdefault("entities", [])
    parsed.setdefault("relationships", [])
    parsed.setdefault("facts", [])
    logger.info(
        "Extracted %d entities, %d relationships, %d facts",
        len(parsed["entities"]),
        len(parsed["relationships"]),
        len(parsed["facts"]),
    )
    return parsed


# ── Answer Generation ──────────────────────────────────────────

GENERATION_SYSTEM_PROMPT = """\
You are a helpful assistant with Long-Term Memory.

Answer the user's question using ONLY the provided MEMORY CONTEXT.
- If the memory context contains relevant info, cite it explicitly
  (e.g., "As you mentioned earlier...").
- If the memory is empty or irrelevant, answer generally but admit
  you don't recall specific details about the user.
- Be concise but thorough.
"""


async def generate_answer(query: str, context: str) -> str:
    """Generate a memory-augmented answer."""
    user_prompt = f"MEMORY CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}"
    return await asyncio.to_thread(_chat, GENERATION_SYSTEM_PROMPT, user_prompt)


def _chat_stream(system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Generator[str, None, None]:
    """Streaming version of _chat. Yields text chunks. Tries Groq first, then Gemini."""
    model = model or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    # ── Try Groq streaming ──
    groq = _get_groq_client()
    if groq is not None:
        try:
            stream = groq.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            return
        except Exception as exc:
            logger.warning("Groq streaming failed, falling back to Gemini: %s", exc)

    # ── Try Gemini streaming ──
    gemini = _get_gemini_client()
    if gemini is not None:
        try:
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            response = gemini.models.generate_content_stream(
                model=gemini_model,
                contents=f"{system_prompt}\n\n---\n\n{user_prompt}",
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as exc:
            logger.error("Gemini streaming also failed: %s", exc)

    raise RuntimeError(
        "No LLM provider available. "
        "Set GROQ_API_KEY or GEMINI_API_KEY in your .env file."
)


def generate_answer_stream(query: str, context: str) -> Generator[str, None, None]:
    """Streaming version of generate_answer. Yields text chunks."""
    user_prompt = f"MEMORY CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}"
    yield from _chat_stream(GENERATION_SYSTEM_PROMPT, user_prompt)


# ── Keyword Extraction ─────────────────────────────────────────

KEYWORD_SYSTEM_PROMPT = """\
Extract the most important keywords/entities from the user's question.
Return ONLY a JSON array of strings. Example: ["React", "hooks", "JavaScript"]
No markdown, no explanation — just the JSON array.
"""


async def extract_keywords(query: str) -> list[str]:
    """Extract search keywords from a user query."""
    raw = await asyncio.to_thread(_chat, KEYWORD_SYSTEM_PROMPT, query)
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        keywords = json.loads(cleaned)
        if isinstance(keywords, list):
            return [str(k) for k in keywords]
    except json.JSONDecodeError:
        pass
    # Fallback
    logger.warning("Keyword extraction fallback — splitting query words.")
    stop_words = {"i", "me", "my", "the", "a", "an", "is", "are", "was",
                  "were", "do", "does", "did", "what", "how", "why", "when",
                  "where", "who", "which", "about", "with", "for", "on",
                  "in", "to", "of", "and", "or", "not", "it", "this", "that",
                  "can", "could", "should", "would", "will", "have", "has",
                  "had", "been", "be", "am", "tell", "know", "remember"}
    words = re.findall(r"\b[a-zA-Z]{2,}\b", query)
    return [w for w in words if w.lower() not in stop_words]


# ── Learning Roadmap Generation ────────────────────────────────

ROADMAP_SYSTEM_PROMPT = """\
You are a Learning Path Planner. Given a target skill and the user's
existing knowledge (from memory), create a step-by-step learning roadmap.

Output a valid JSON object with these keys:
1. "steps": a list of objects, each with:
   - "order" (int, starting from 1)
   - "topic" (string — the topic/concept to learn)
   - "description" (string — what to study and why)
   - "already_known" (bool — true if the user already knows this)
   - "prerequisites" (list of strings — topics that should be learned first)
   - "resources" (list of strings — suggested learning resources)
2. "estimated_time" (string — rough time estimate, e.g. "4-6 weeks")

Rules:
- Build a logical prerequisite chain from fundamentals to the target skill.
- Mark topics the user already knows as already_known=true.
- Suggest 2-3 practical resources per step (courses, docs, tutorials).
- Keep steps focused — 5 to 10 steps maximum.
- Output ONLY the JSON object.
"""


async def generate_learning_roadmap(target_skill: str, context: str) -> dict:
    """Generate a personalized learning roadmap.

    Parameters
    ----------
    target_skill : str
        The skill the user wants to learn.
    context : str
        User's existing knowledge from the graph.

    Returns
    -------
    dict
        Keys: ``steps``, ``estimated_time``.
    """
    user_prompt = (
        f"EXISTING KNOWLEDGE:\n{context}\n\n"
        f"TARGET SKILL: {target_skill}\n\n"
        "Create a personalized learning roadmap."
    )
    raw = await asyncio.to_thread(_chat, ROADMAP_SYSTEM_PROMPT, user_prompt)
    parsed = _parse_json_from_llm(raw)
    parsed.setdefault("steps", [])
    parsed.setdefault("estimated_time", "")
    return parsed
