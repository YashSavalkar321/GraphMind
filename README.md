# GraphMind

> Memory-grounded AI chat with a personal knowledge graph — built with React + FastAPI + Neo4j + Groq/Gemini.

---

## Tech Stack

| Layer        | Technology                                         |
| ------------ | -------------------------------------------------- |
| Frontend     | React 19 + Vite 8 + Tailwind CSS v4               |
| State        | Zustand 5                                          |
| Graph UI     | @xyflow/react 12 (React Flow)                      |
| Icons        | lucide-react, react-icons                          |
| Backend      | FastAPI (Python 3.11+) + Uvicorn                   |
| Auth         | Clerk (RS256 JWKS) + own HS256 JWT (dual mode)     |
| Graph DB     | Neo4j — indexed, MERGE-based entity resolution     |
| Embeddings   | sentence-transformers — all-MiniLM-L6-v2 (384-dim, GPU/CPU) |
| In-Memory    | CQRS engine — pyahocorasick + multi-source BFS     |
| LLM          | Groq (llama-3.3-70b) / Gemini (gemini-1.5-flash)  |

---

## Project Structure

```
GraphMind/
├── .env                             # All configuration (Neo4j, LLM, auth, etc.)
├── README.md
│
├── backend/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app — all routes, CORS, CQRS engine, SSE
│   ├── auth.py                      # Clerk JWT + HS256 JWT + X-User-Id fallback
│   ├── database.py                  # Neo4j singleton, schema constraints, query helpers
│   ├── models.py                    # Pydantic request/response schemas
│   ├── worker.py                    # LLM extraction prompt, graph merge logic
│   ├── memory_ops.py                # Graph retrieval, user profile, mindmap data
│   ├── memory_store.py              # In-memory CQRS store (Aho-Corasick + BFS)
│   ├── llm_service.py               # Groq / Gemini HTTP client + answer generation
│   ├── vector_store.py              # Sentence-transformers embeddings + cosine search
│   └── requirements.txt             # Python dependencies
│
└── frontend/
    ├── index.html
    ├── vite.config.js               # Dev proxy: /api → http://localhost:8000
    ├── package.json
    └── src/
        ├── App.jsx                  # Root layout (navbar + sidebar + split panels)
        ├── main.jsx                 # Entry point
        ├── index.css                # Design tokens, animations, utilities
        ├── components/
        │   ├── Navbar.jsx           # Top bar — logo, ingest, user switcher, auth modal
        │   ├── ChatSidebar.jsx      # Left sidebar — chat history, pin, search, delete
        │   ├── ChatWindow.jsx       # Chat panel — messages, input, citations
        │   ├── GraphCanvas.jsx      # Mindmap — React Flow, filter toggles, focus mode
        │   ├── IngestModal.jsx      # Document ingestion modal (text + file upload)
        │   ├── CitationBadge.jsx    # Memory citation pill + subgraph viewer
        │   ├── PerformanceTimer.jsx # Retrieval time badge
        │   ├── LoadingSpinner.jsx   # Spinner component
        │   ├── ErrorBoundary.jsx    # React error boundary
        │   └── Toast.jsx            # Toast notification
        ├── store/
        │   └── useAppStore.js       # Zustand global store (API calls + mock fallback)
        ├── hooks/
        │   └── useGraphHighlight.js # Graph node highlight on citation click
        └── data/
            └── mockData.js          # Mock data (fallback when backend is offline)
```

---

## Features

### Frontend — UI

- **Split-panel layout** — resizable chat + mindmap side-by-side on desktop; tabbed view on mobile.
- **JWT authentication** — Sign Up / Login modal with JWT stored in `localStorage`; all API calls include `Authorization: Bearer` header.
- **Memory-grounded chat** — AI responses include retrieval time and memory citations that link to graph nodes.
- **Knowledge graph (Mindmap)** — interactive React Flow canvas with zoom, minimap, and detail panel on click. Five color-coded node types: **Entity** (purple), **Preference** (pink), **Goal** (teal), **Event** (orange), and **Fact** (green). Interactive filter toggles let you show/hide node categories. Click any node to focus its neighbourhood and reveal connected facts.
- **Document ingestion** — modal with drag-and-drop file upload (PDF, TXT, MD) or paste text; chunks are extracted into the knowledge graph.
- **Auth-aware Navbar** — shows Login/Sign Up when unauthenticated; shows user avatar + Sign Out when authenticated.
- **Mock-data fallback** — the frontend works standalone with local mock data when the backend is unreachable.

### Chat Sidebar

- **Collapsible left sidebar** toggled via a button pinned below the navbar.
- **New Chat** — creates a fresh chat session; the previous session is auto-saved.
- **Chat history list** — every conversation is displayed with title, message count, and relative timestamp.
- **Pin / Unpin chats** — context menu (three-dot icon) to pin important chats to the top.
- **Delete chat** — remove any chat session from the same context menu.
- **Search** — filter chat history by title.
- **Auto-title** — chat title is derived from the first user message.

### Backend — Hybrid Retrieval Pipeline

- **Dual auth** — Clerk RS256 JWT (production) + own HS256 JWT (dev) + `X-User-Id` header fallback. Auth priority: HS256 → Clerk → header → query param → 401.
- **In-memory CQRS engine** — on login/signup, the user's full graph is loaded into RAM. Read path uses Aho-Corasick automaton + multi-source BFS for <15ms retrieval with zero Neo4j queries.
- **SSE streaming** — `/chat/stream` streams the LLM answer token-by-token via Server-Sent Events.
- **High-fidelity entity resolution** — new entities are resolved against existing graph nodes using `MERGE` + `toLower()` normalization, preventing duplicates.
- **Priority-based LLM extraction** — ingested text is processed by a strict JSON system prompt with priority-based classification rules. The LLM extracts nodes into five categories (goal → preference → event → fact → entity) with the first matching rule winning.
- **Hierarchical graph structure** — nodes are organized as `User → Category → Entity` with facts linked via `HAS_FACT` relationships.
- **Hybrid vector + graph retrieval** — sentence-transformers embeddings (all-MiniLM-L6-v2) provide semantic search alongside Aho-Corasick keyword matching.
- **Neo4j indexing** — startup creates uniqueness constraints and composite indexes for <100ms reads.
- **Background graph sync** — after each chat message, knowledge extraction and graph MERGE run asynchronously without blocking the response.
- **User isolation** — every Neo4j query includes `WHERE n.user_id = $uid`.
- **Graceful degradation** — backend starts even if Neo4j is unavailable; features degrade gracefully.
- **Learning path planner** — `/roadmap` generates a personalized learning roadmap based on the user's existing knowledge graph.
- **No pre-built memory frameworks** — built with `neo4j`, `fastapi`, `groq`, `google-genai`, `sentence-transformers`, and `pyahocorasick` only.

### API Endpoints

| Method | Path               | Description                                              |
| ------ | ------------------ | -------------------------------------------------------- |
| GET    | `/health`          | Service health check (Neo4j status, active sessions)     |
| POST   | `/auth/signup`     | Register user → create Neo4j User node → return JWT      |
| POST   | `/auth/login`      | Verify credentials → return JWT                          |
| POST   | `/session/init`    | Warm up in-memory CQRS session (auto-called on auth)     |
| POST   | `/chat`            | Hybrid retrieve → LLM generate → auto-ingest to graph    |
| POST   | `/chat/stream`     | Same as `/chat` but streams answer via SSE               |
| POST   | `/ingest`          | Ingest text into the knowledge graph                     |
| POST   | `/memory/ingest`   | Frontend-compatible ingest with auto-chunking             |
| POST   | `/upload`          | Upload PDF/TXT/MD file → extract text → ingest           |
| GET    | `/mindmap`         | User's knowledge graph (raw nodes + edges)               |
| GET    | `/memory/mindmap`  | Knowledge graph in React Flow format (positioned nodes)  |
| GET    | `/chats`           | List all chat sessions for a user                        |
| POST   | `/chats`           | Save or update a chat session                            |
| DELETE | `/chats/{chat_id}` | Delete a chat session                                    |
| GET    | `/profile`         | User knowledge profile (entities, types, fact counts)    |
| POST   | `/roadmap`         | Generate personalized learning roadmap for a target skill|

---

## Prerequisites

| Tool       | Version / Notes                                    |
| ---------- | -------------------------------------------------- |
| Node.js    | v18+ (for the frontend)                            |
| Python     | 3.11+ (for the backend)                            |
| Docker     | Docker Desktop or Docker Engine (for Neo4j)        |

> **LLM:** By default, uses Groq (llama-3.3-70b-versatile). Set `GEMINI_API_KEY` in `.env` to use Google Gemini instead.

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

#### 1. Start Neo4j (Docker)

```bash
docker run -d \
  --name graphmind-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/graphmind123 \
  -v graphmind_neo4j_data:/data \
  neo4j:latest

# Verify — open http://localhost:7474 in a browser (Neo4j Browser UI)
```

#### 2. Configure environment

Edit `.env` in the project root:

```dotenv
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphmind123

# LLM — Groq (primary)
GROQ_API_KEY=your_groq_api_key_here

# LLM — Gemini (fallback)
GEMINI_API_KEY=your_gemini_api_key_here

# LLM model
LLM_MODEL=llama-3.3-70b-versatile

# JWT Auth
JWT_SECRET=graphmind-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# Clerk (optional — for production auth)
CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_key_here
```

#### 3. Install Python dependencies & start backend

```bash
cd backend

# Create virtual env (recommended)
python -m venv .venv
source .venv/bin/activate    # Linux/WSL
# .venv\Scripts\activate     # Windows

pip install -r requirements.txt

# Start the API server (from project root)
cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:

```
INFO  │ Neo4j connectivity verified ✓
INFO  │ Embedding model loaded (all-MiniLM-L6-v2)
INFO  │ GraphMind backend started ✓
INFO  │ Application startup complete.
```

#### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`.

---

## Environment Variables Reference

| Variable               | Default                               | Description                              |
| ---------------------- | ------------------------------------- | ---------------------------------------- |
| `NEO4J_URI`            | `bolt://localhost:7687`               | Neo4j Bolt endpoint                      |
| `NEO4J_USER`           | `neo4j`                               | Neo4j username                           |
| `NEO4J_PASSWORD`       | `graphmind123`                        | Neo4j password                           |
| `GROQ_API_KEY`         | *(empty)*                             | Groq API key (primary LLM)               |
| `GEMINI_API_KEY`       | *(empty)*                             | Gemini API key (fallback LLM)            |
| `LLM_MODEL`            | `llama-3.3-70b-versatile`            | LLM model name                           |
| `JWT_SECRET`           | `graphmind-change-me-in-prod`        | Secret key for HS256 JWT signing         |
| `JWT_ALGORITHM`        | `HS256`                               | JWT signing algorithm                    |
| `JWT_EXPIRY_HOURS`     | `24`                                  | JWT token lifetime in hours              |
| `CLERK_PUBLISHABLE_KEY`| *(empty)*                             | Clerk publishable key (optional)         |
| `CLERK_SECRET_KEY`     | *(empty)*                             | Clerk secret key (optional)              |
| `APP_ENV`              | `development`                         | Application environment                  |
| `BACKEND_URL`          | `http://localhost:8000`               | Backend URL (used by frontend)           |

---

## Debugging

### Backend — FastAPI

**Live reload:**
The server starts with `--reload`, so any change to Python files restarts the server automatically.

**Interactive API docs:**
FastAPI auto-generates OpenAPI docs:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

**Health check:**

```bash
curl http://localhost:8000/health
# → {"status":"ok","neo4j":true,"version":"2.0.0","active_sessions":0,"architecture":"in-memory-cqrs-sse"}
```

**Test signup:**

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com","password":"secret123"}'
# → {"user_id":"user_...","name":"Alice","email":"alice@example.com","token":"eyJ..."}
```

**Test chat:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id":"user_1","query":"What do you know about me?"}'
```

**Test mindmap:**

```bash
curl http://localhost:8000/memory/mindmap?user_id=user_1
```

**Common issues:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Neo4j connectivity check failed` | Neo4j container not running | `docker start graphmind-neo4j` |
| `LLM call failed` | Groq/Gemini API key missing or invalid | Check `GROQ_API_KEY` and `GEMINI_API_KEY` in `.env` |
| Port 8000 already in use | Another process on port 8000 | Kill it or use `--port 8001` and update `vite.config.js` proxy |

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

**API proxy:**
Vite proxies `/api/*` → `http://localhost:8000/*` (path rewrite strips `/api` prefix). If the backend is on a different port, update `frontend/vite.config.js`.

**Mock fallback:**
Every API call wraps the fetch in try/catch and falls back to local mock data from `src/data/mockData.js`. The frontend always works — even without the backend running.

### Neo4j

- **Browser UI:** [http://localhost:7474](http://localhost:7474)
- **Credentials:** `neo4j` / `graphmind123` (or whatever `NEO4J_PASSWORD` is set to)
- **Useful Cypher queries:**

```cypher
-- See all nodes for a user
MATCH (n) WHERE n.user_id = 'user_1' RETURN n LIMIT 50;

-- See graph hierarchy (User → Category → Entity)
MATCH (u:User)-[:HAS_CATEGORY]->(c:Category)-[:CONTAINS]->(e:Entity)
WHERE u.user_id = 'user_1'
RETURN u, c, e;

-- See facts linked to entities
MATCH (e:Entity)-[:HAS_FACT]->(f:Fact)
WHERE e.user_id = 'user_1'
RETURN e.name, f.name, f.snippet;

-- Count nodes by label
MATCH (n) WHERE n.user_id = 'user_1' RETURN labels(n)[0] AS type, count(*) AS count;

-- Delete all data for a user
MATCH (n) WHERE n.user_id = 'user_1' DETACH DELETE n;
```

### Resetting Data

```bash
# Reset Neo4j (delete all nodes and relationships)
docker exec graphmind-neo4j cypher-shell -u neo4j -p graphmind123 "MATCH (n) DETACH DELETE n"

# Restart backend to recreate indexes
# (Ctrl+C the uvicorn process and re-run it)
```
