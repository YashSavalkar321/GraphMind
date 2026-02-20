# UI/UX, Architecture, and Quality Assurance Requirements

## 1. Frontend & Visualization (Member 3)
This section outlines the strict user interface and visual requirements for the GraphMind application.

* **Multi-User Interface:** The UI must support multiple users with strictly isolated memory spaces. A user-switcher or login dropdown is required to demonstrate this context switching.
* **Mindmap Visualization:** The UI (Streamlit, React, or CLI) must visually display the memory graph (mindmap). It must show the nodes and edges fetched from the backend.
* **Memory Citations (Auditability):** When generating an answer, the chat interface must clearly show what memories were used (e.g., brief citations, node IDs, titles, or source snippets).
* **Performance Metrics Display (MANDATORY):** For every query, the UI must display the RAG Retrieval Time (graph query + vector search + context assembly).
* **Format Strictness:** The retrieval time must exclude LLM response generation time. The display format must specifically be: "Retrieval completed in X ms".

## 2. Systems, QA, and Deliverables (Member 4)
This section outlines the architectural documentation, testing, and final submission requirements.

* **Graceful Fallbacks (QA):** The system must gracefully handle "I don't know / not in memory" scenarios without hallucinating.
* **Repository Standards:** The final submission must include a GitHub repository with clean, easy-to-follow setup instructions.
* **Architecture Documentation:** An Architecture Diagram (High-Level Design / HLD) must be provided along with a brief explanation of the components.
* **API Documentation:** Clear documentation of all endpoints with request and response examples must be provided.
* **Demo Video:** A 3-5 minute video or live demo is required.
* **Demo Checklist:** The demo must explicitly show:
    * Memory ingestion.
    * Mindmap/graph visualization.
    * Hybrid retrieval with the retrieval time clearly displayed.
    * The final grounded answer with evidence.