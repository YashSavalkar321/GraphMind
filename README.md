# GraphMind

> Memory-grounded AI chat with a personal knowledge graph — built with React + FastAPI + Neo4j + Qdrant + Ollama.

---

## Tech Stack

| Layer        | Technology                                      |
| ------------ | ----------------------------------------------- |
| Frontend     | React 19 + Vite 8 + Tailwind CSS v4             |
| State        | Zustand 5                                       |
| Graph UI     | @xyflow/react 12 (React Flow)                   |
| Icons        | lucide-react, react-icons                       |
| Backend      | FastAPI (Python 3.11+) + Uvicorn                |
| Graph DB     | Neo4j (Docker)                                  |
| Vector DB    | Qdrant (Docker or local file-based fallback)    |
| Embeddings   | fastembed — BAAI/bge-small-en-v1.5 (384-dim, local CPU) |
| LLM          | Ollama (llama3.1, local) / Groq / Gemini        |
| Containers   | Docker Compose (WSL2 / Docker Desktop)          |

---

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx                  # Root layout (navbar + sidebar + split panels)
│   ├── main.jsx                 # Entry point
│   ├── index.css                # Design tokens, animations, utilities
│   ├── components/
│   │   ├── Navbar.jsx           # Top bar — logo, ingest button, user switcher
│   │   ├── ChatSidebar.jsx      # Left sidebar — chat history, pin, new chat
│   │   ├── ChatWindow.jsx       # Chat panel — messages, input, citations
│   │   ├── GraphCanvas.jsx      # Mindmap panel — React Flow graph
│   │   ├── IngestModal.jsx      # Document ingestion modal
│   │   ├── CitationBadge.jsx    # Memory citation pill
│   │   ├── PerformanceTimer.jsx # Retrieval time badge
│   │   ├── LoadingSpinner.jsx   # Spinner component
│   │   ├── ErrorBoundary.jsx    # React error boundary
│   │   └── Toast.jsx            # Toast notification
│   ├── store/
│   │   └── useAppStore.js       # Zustand global store (API calls + mock fallback)
│   ├── hooks/
│   │   └── useGraphHighlight.js # Graph node highlight hook
│   └── data/
│       └── mockData.js          # Mock data (fallback when backend is offline)

sdBackend/
├── docker-compose.yml           # Neo4j + Qdrant + FastAPI orchestration
├── Dockerfile                   # Python 3.11-slim + fastembed model pre-warm
├── requirements.txt             # fastapi, neo4j, qdrant-client, fastembed, httpx
├── .env / .env.example          # LLM provider & service connection strings
├── app/
│   ├── main.py                  # FastAPI app — CORS, async lifespan, routers
│   ├── config.py                # Pydantic settings from environment
│   ├── models.py                # Request/response schemas (matches frontend contract)
│   ├── routers/
│   │   ├── ingest.py            # POST /memory/ingest
│   │   ├── chat.py              # POST /chat
│   │   └── mindmap.py           # GET  /memory/mindmap
│   └── services/
│       ├── neo4j_client.py      # Async Neo4j driver wrapper
│       ├── vector_client.py     # Qdrant client (remote or local file fallback)
│       ├── embeddings.py        # Local fastembed (bge-small-en-v1.5)
│       ├── llm_client.py        # Ollama / Groq / Gemini HTTP client
│       ├── extraction.py        # LLM-based knowledge graph extraction
│       ├── retrieval.py         # Hybrid parallel retrieval + LLM generation
│       └── chunking.py          # Sentence-aware text chunking
```

---

## Features

### Frontend — UI

- **Split-panel layout** — resizable chat + mindmap side-by-side on desktop; tabbed view on mobile.
- **Memory-grounded chat** — AI responses include retrieval time and memory citations that link to graph nodes.
- **Knowledge graph (Mindmap)** — interactive React Flow canvas with zoom, minimap, color-coded node types, and detail panel on click.
- **Document ingestion** — modal with drag-and-drop file upload or paste text; chunks are visualized as new graph nodes.
- **Multi-user switching** — dropdown to switch between demo users; each has isolated docs, graph, and chat history.
- **Mock-data fallback** — the frontend works standalone with local mock data when the backend is unreachable.

### Chat Sidebar

- **Collapsible left sidebar** toggled via a button pinned below the navbar.
- **New Chat** — creates a fresh chat session; the previous session is auto-saved.
- **Chat history list** — every conversation is displayed with title, message count, and relative timestamp.
- **Pin / Unpin chats** — context menu (three-dot icon) to pin important chats to the top.
- **Delete chat** — remove any chat session from the same context menu.
- **Search** — filter chat history by title.
- **Auto-title** — chat title is derived from the first user message.

### Backend — Hybrid RAG Pipeline

- **Parallel retrieval** — Vector DB (Qdrant) and Graph DB (Neo4j) are queried simultaneously via `asyncio.gather`.
- **Hybrid fusion** — results are deduplicated by `memory_id` and assembled into a single context window.
- **Performance timer** — `time.perf_counter()` wraps *only* the DB fetch + context assembly; the timer stops **before** LLM generation.
- **LLM extraction** — ingested text is processed by a strict JSON system prompt that outputs `{nodes, edges}` for the knowledge graph.
- **User isolation** — every Neo4j query includes `WHERE n.user_id = $user_id`; Qdrant search uses a payload filter on `user_id`.
- **Graceful degradation** — backend starts even if Neo4j or Qdrant are unavailable; Qdrant auto-falls back to local file-based storage.
- **No pre-built memory frameworks** — built with `neo4j`, `qdrant-client`, `fastapi`, `fastembed`, and `httpx` only.

### API Endpoints

| Method | Path               | Description                          |
| ------ | ------------------ | ------------------------------------ |
| POST   | `/memory/ingest`   | Chunk → embed → extract graph → store in Neo4j + Qdrant |
| GET    | `/memory/mindmap`  | All nodes & edges for a user (React Flow format) |
| POST   | `/chat`            | Hybrid retrieve → LLM generate (with citations) |
| GET    | `/health`          | Service health check                 |

---

## Prerequisites

| Tool       | Version / Notes                                    |
| ---------- | -------------------------------------------------- |
| Node.js    | v18+ (for the frontend)                            |
| Python     | 3.11+ (for the backend)                            |
| Docker     | Docker Desktop **or** Docker Engine inside WSL2    |
| Ollama     | Local install — `ollama pull llama3.1` (default LLM) |

> **Alternative LLMs:** set `LLM_PROVIDER=groq` or `LLM_PROVIDER=gemini` in `.env` and supply the corresponding API key instead of using Ollama.

---

## How to Run

### Option A — Frontend only (mock data, no backend needed)

```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

The app renders with built-in mock data. Chat and mindmap work in demo mode.

### Option B — Full stack (recommended)

#### 1. Start Ollama

```bash
# Pull the model once
ollama pull llama3.1

# Start the server (Windows — bind to all interfaces so WSL can reach it)
set OLLAMA_HOST=0.0.0.0
ollama serve

# Verify
curl http://localhost:11434/       # → "Ollama is running"
```

> **WSL note:** If you run the backend inside WSL while Ollama runs on Windows, set `OLLAMA_HOST=0.0.0.0` before starting Ollama so WSL can reach it via the gateway IP. Update `OLLAMA_BASE_URL` in `.env` to `http://<WINDOWS_HOST_IP>:11434` (find it with `ip route show default` inside WSL and use the gateway IP).

#### 2. Start Neo4j (Docker)

```bash
# Using Docker directly:
docker run -d \
  --name graphmind-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/12345678 \
  -e 'NEO4J_PLUGINS=["apoc"]' \
  -v graphmind_neo4j_data:/data \
  neo4j:latest

# Verify — open http://localhost:7474 in a browser (Neo4j Browser UI)
```

#### 3. Start Qdrant (optional — backend auto-falls back to local file storage)

```bash
docker run -d \
  --name graphmind-qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v graphmind_qdrant_data:/qdrant/storage \
  qdrant/qdrant:latest
```

> If you skip this step, the backend uses local file-based Qdrant storage in `sdBackend/.qdrant_local/`. This is fine for development.

#### 4. Configure environment

```bash
cd sdBackend
cp .env.example .env
```

Edit `sdBackend/.env`:

```dotenv
# LLM (default: Ollama local)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434   # or http://<WSL_GATEWAY_IP>:11434
OLLAMA_MODEL=llama3.1

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678

# Qdrant (ignored if Qdrant container is not running — falls back to local)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

#### 5. Install Python dependencies & start backend

```bash
cd sdBackend

# Create virtual env (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/WSL:
source .venv/bin/activate

pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:

```
INFO  │ Neo4j connected at bolt://localhost:7687
WARN  │ Remote Qdrant unavailable, using local file-based storage   # (if no Qdrant container)
INFO  │ Embedding model loaded
INFO  │ ✅ Startup complete
INFO  │ Application startup complete.
```

#### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`. If the backend is down, the UI falls back to mock data automatically.

### Option C — Docker Compose (all-in-one)

```bash
cd sdBackend
docker compose up -d     # Starts Neo4j + Qdrant + FastAPI

# Then start the frontend separately:
cd ../frontend
npm install
npm run dev
```

> Docker Compose requires all three images to pull from Docker Hub. If you see TLS errors, use Option B instead.

---

## Environment Variables Reference

| Variable            | Default                        | Description                              |
| ------------------- | ------------------------------ | ---------------------------------------- |
| `LLM_PROVIDER`      | `ollama`                       | `ollama`, `groq`, or `gemini`            |
| `OLLAMA_BASE_URL`   | `http://localhost:11434`       | Ollama server URL                        |
| `OLLAMA_MODEL`      | `llama3.1`                     | Ollama model name                        |
| `GROQ_API_KEY`      | *(empty)*                      | Groq API key (if using Groq)             |
| `GROQ_MODEL`        | `llama-3.3-70b-versatile`      | Groq model name                          |
| `GEMINI_API_KEY`    | *(empty)*                      | Gemini API key (if using Gemini)         |
| `GEMINI_MODEL`      | `gemini-1.5-flash`             | Gemini model name                        |
| `NEO4J_URI`         | `bolt://localhost:7687`        | Neo4j Bolt endpoint                      |
| `NEO4J_USER`        | `neo4j`                        | Neo4j username                           |
| `NEO4J_PASSWORD`    | `graphmind123`                 | Neo4j password                           |
| `QDRANT_HOST`       | `localhost`                    | Qdrant server host                       |
| `QDRANT_PORT`       | `6333`                         | Qdrant server port                       |
| `QDRANT_COLLECTION` | `graphmind_chunks`             | Qdrant collection name                   |
| `EMBEDDING_MODEL`   | `BAAI/bge-small-en-v1.5`      | fastembed model (384-dim)                |
| `CORS_ORIGINS`      | `http://localhost:5173,...`     | Comma-separated allowed origins          |
| `LOG_LEVEL`         | `info`                         | Python logging level                     |

---

## Debugging

### Backend — FastAPI

**Live reload:**
The server starts with `--reload`, so any change to Python files in `sdBackend/app/` restarts the server automatically.

**Logs:**
All backend logs use structured format: `HH:MM:SS │ LEVEL │ module │ message`. Set `LOG_LEVEL=debug` in `.env` for verbose output.

**Interactive API docs:**
FastAPI auto-generates OpenAPI docs:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

**Health check:**

```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"graphmind-api"}
```

**Test ingestion manually:**

```bash
curl -X POST http://localhost:8000/memory/ingest \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_1","title":"Test Doc","text":"Your text here.","source_type":"text"}'
```

**Test chat manually:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_1","query":"What did I just ingest?"}'
```

**Test mindmap:**

```bash
curl http://localhost:8000/memory/mindmap?user_id=user_1
```

**Common issues:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Neo4j unavailable` at startup | Neo4j container not running | `docker start graphmind-neo4j` or re-run the `docker run` command |
| `Remote Qdrant unavailable, using local file-based storage` | Qdrant container not running | This is fine for dev — local file storage works. Or start the Qdrant container. |
| `All connection attempts failed` (LLM) | Ollama not running or not reachable | Start Ollama: `ollama serve`. If running backend in WSL, ensure `OLLAMA_HOST=0.0.0.0` and update `OLLAMA_BASE_URL` in `.env` |
| `TLS handshake timeout` pulling Docker images | Docker Hub connectivity issue | Retry later, use a VPN, or use Option B (run services manually) |
| `Entity extraction LLM call failed` | LLM timeout / unreachable | Non-fatal — ingestion still creates a document node. Check Ollama status. |
| Port 8000 already in use | Another process on port 8000 | Kill it or use `--port 8001` and update `vite.config.js` proxy target |

### Frontend — Vite + React

**Dev server:**

```bash
cd frontend
npm run dev         # → http://localhost:5173 (HMR enabled)
```

**Build for production:**

```bash
npm run build       # Output in frontend/dist/
npm run preview     # Serve the production build locally
```

**Lint:**

```bash
npm run lint        # ESLint with React hooks + refresh plugins
```

**API proxy:**
Vite proxies `/api/*` → `http://localhost:8000/*` (path rewrite strips `/api` prefix). If the backend is on a different port, update [frontend/vite.config.js](frontend/vite.config.js).

**Mock fallback:**
Every API call (`sendMessage`, `ingestDocument`, `fetchMindmap`) wraps the fetch in try/catch and falls back to local mock data from `src/data/mockData.js`. This means the frontend always works — even without the backend running.

### Neo4j

- **Browser UI:** [http://localhost:7474](http://localhost:7474)
- **Credentials:** `neo4j` / `12345678` (or whatever `NEO4J_PASSWORD` is set to)
- **Useful Cypher queries:**

```cypher
-- See all nodes for a user
MATCH (n) WHERE n.user_id = 'user_1' RETURN n LIMIT 50;

-- See all relationships
MATCH (a)-[r]->(b) WHERE a.user_id = 'user_1' RETURN a, r, b LIMIT 50;

-- Count nodes by label
MATCH (n) WHERE n.user_id = 'user_1' RETURN labels(n)[0] AS type, count(*) AS count;

-- Delete all data for a user
MATCH (n) WHERE n.user_id = 'user_1' DETACH DELETE n;
```

### Resetting Data

```bash
# Reset Neo4j (delete all nodes and relationships)
docker exec graphmind-neo4j cypher-shell -u neo4j -p 12345678 "MATCH (n) DETACH DELETE n"

# Reset Qdrant local storage
rm -rf sdBackend/.qdrant_local/

# Restart backend to recreate collections
# (Ctrl+C the uvicorn process and re-run it)
```

---

## Changelog

### 2026-02-20 — Full Backend + Ollama Integration

**Backend created (`sdBackend/`):**
- `docker-compose.yml` — orchestrates Neo4j, Qdrant, and FastAPI containers.
- `Dockerfile` — Python 3.11-slim with fastembed model pre-downloaded at build time.
- `app/main.py` — FastAPI app with CORS, graceful async lifespan (DB connections + model warm-up).
- `app/config.py` — Pydantic-based settings loaded from `.env`.
- `app/models.py` — All request/response schemas matching the frontend contract.
- `app/routers/ingest.py` — Chunking → LLM extraction → Neo4j + Qdrant storage.
- `app/routers/chat.py` — Parallel hybrid retrieval (timed) → LLM generation.
- `app/routers/mindmap.py` — Neo4j query → auto-layout → React Flow format.
- `app/services/neo4j_client.py` — Async Neo4j driver with indexes, CRUD, neighborhood search.
- `app/services/vector_client.py` — Qdrant client with remote/local fallback and user-filtered search.
- `app/services/embeddings.py` — Local CPU embeddings via fastembed (BAAI/bge-small-en-v1.5).
- `app/services/llm_client.py` — Ollama / Groq / Gemini HTTP client with JSON parsing.
- `app/services/extraction.py` — Knowledge graph extraction via engineered system prompts.
- `app/services/retrieval.py` — Parallel vector + graph retrieval, hybrid fusion, LLM answer.
- `app/services/chunking.py` — Sentence-aware text chunking with overlap.

**Frontend modified:**
- `vite.config.js` — Added dev proxy: `/api` → `http://localhost:8000`.
- `store/useAppStore.js` — `sendMessage`, `ingestDocument`, `fetchMindmap` now call real API; auto-fallback to mock data when backend is offline.

### 2026-02-20 — Chat Sidebar

**Files added:**
- `frontend/src/components/ChatSidebar.jsx` — Sidebar with chat history, pin, new chat, search, delete.

**Files modified:**
- `frontend/src/store/useAppStore.js` — Sidebar state + chat history management actions.
- `frontend/src/App.jsx` — Sidebar integrated; content shifts on desktop.
- `frontend/src/index.css` — Slide-in animation.
