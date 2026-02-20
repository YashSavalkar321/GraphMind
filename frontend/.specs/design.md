# Frontend Architecture & DevOps Design (HLD)

## 1. UI Architecture (Member 3 Focus)
The frontend will be built as a Single Page Application (SPA) to ensure dynamic rendering of both the chat interface and the memory mindmap without page reloads.



* **Framework:** React (Next.js or Vite).
* **Graph Visualization Library:** `react-flow-renderer` or `cytoscape.js`. [cite_start]These libraries allow dynamic rendering of the JSON payload returned by the `GET /memory/mindmap` endpoint [cite: 110-112].
* **State Management:** React Context or Zustand to globally manage the `current_user_id`. [cite_start]This ensures that every API call to `/chat` and `/memory/mindmap` is strictly scoped to the active user, preventing data leakage[cite: 93, 111, 114].
* **Component Structure:**
    * `Sidebar.jsx`: User switcher, history of ingested documents.
    * `ChatWindow.jsx`: Message thread, input box.
    * [cite_start]`CitationBadge.jsx`: Reusable component to parse and display `memory_citations` arrays[cite: 118].
    * [cite_start]`PerformanceTimer.jsx`: A strict UI component fixed below the AI response rendering "Retrieval completed in X ms"[cite: 50].
    * `GraphCanvas.jsx`: The interactive mindmap container.

## 2. DevOps & System Design (Member 4 Focus)
[cite_start]The infrastructure must be fully containerized to ensure the judges can easily run the application locally, fulfilling the "clean setup instructions" requirement[cite: 83].



* **Containerization:** `docker-compose.yml` will be used to orchestrate the entire stack (Frontend container, FastAPI Backend container, Neo4j container, Milvus container).
* [cite_start]**API Documentation:** The backend's auto-generated Swagger UI (provided by FastAPI) will be configured and exported to fulfill the API documentation deliverable[cite: 86].
* **QA Testing Strategy:**
    * [cite_start]**Unit Testing:** Verify the frontend correctly formats the `retrieval_time_ms`[cite: 50, 117].
    * [cite_start]**Integration Testing:** Verify the frontend correctly handles the API endpoints: `POST /memory/ingest`, `GET /memory/mindmap`, `POST /chat`, and `GET /health` [cite: 107-122].
    * [cite_start]**Edge Case Testing (QA Trigger):** Manually inject queries with zero relevance to trigger and verify the "I don't know" fallback[cite: 45].