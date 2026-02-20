# Task Assignments & Sprint Schedule (M3 & M4)

## Week 1: Foundation, Boilerplate & Contracts
* **[M3] Task 1.1:** Scaffold the React/Next.js frontend application.
* **[M3] Task 1.2:** Build the basic static UI shell (Sidebar, Chat window, Graph placeholder).
* **[M3] Task 1.3:** Implement a mock `UserContext` provider to simulate switching between User A and User B.
* **[M4] Task 1.1:** Initialize the GitHub repository and branch protection rules.
* [cite_start]**[M4] Task 1.2:** Write the baseline `README.md` and draft the initial Architecture Diagram (HLD) [cite: 83-84].
* **[M4] Task 1.3:** Create the `docker-compose.yml` file to spin up the required databases and placeholders for web services.

## Week 2: Visualization & Ingestion UI
* **[M3] Task 2.1:** Integrate `react-flow` (or chosen graph library) into the `GraphCanvas.jsx` component.
* [cite_start]**[M3] Task 2.2:** Connect the frontend to the backend `GET /memory/mindmap` endpoint [cite: 110-112]. Ensure the graph updates dynamically.
* [cite_start]**[M3] Task 2.3:** Build the UI for the `/memory/ingest` endpoint [cite: 107-109], allowing users to upload text or simulate a "learning" mode.
* [cite_start]**[M4] Task 2.1:** QA Test User Isolation: Verify that switching users in the UI completely clears and re-fetches the correct graph canvas data[cite: 93].
* [cite_start]**[M4] Task 2.2:** Setup API documentation generators (Swagger/Postman collections) to map out backend progress[cite: 86].

## Week 3: Chat Integration, Metrics & QA Stress Testing
* [cite_start]**[M3] Task 3.1:** Wire up the `POST /chat` endpoint to the chat interface [cite: 113-120].
* [cite_start]**[M3] Task 3.2:** Implement the `PerformanceTimer.jsx` to intercept `retrieval_time_ms` [cite: 117] [cite_start]and strictly format it as "Retrieval completed in X ms"[cite: 50].
* [cite_start]**[M3] Task 3.3:** Design the citation markers to render the `memory_citations` data (node IDs and snippets) alongside the text response[cite: 44, 118].
* [cite_start]**[M4] Task 3.1:** QA Testing - Hallucinations: Send completely irrelevant prompts to the chat and verify it triggers the "not in memory" condition[cite: 45].
* **[M4] Task 3.2:** QA Testing - Visuals: Verify that when a citation is clicked or rendered, it accurately reflects a node existing on the mindmap.

## Week 4: Deliverables, Polish & The Pitch
* **[M3] Task 4.1:** UI Polish: Add loading states, error boundary handling, and ensure the mindmap auto-arranges cleanly.
* [cite_start]**[M4] Task 4.1:** Finalize the GitHub repository `README.md` with foolproof, step-by-step setup instructions[cite: 83].
* [cite_start]**[M4] Task 4.2:** Finalize the HLD architecture diagram and component explanations[cite: 84].
* **[M4] Task 4.3:** Script, record, and edit the 3-5 minute demo video. [cite_start]Ensure the video clearly highlights ingestion, visualization, retrieval time, and the grounded answer [cite: 87-91].