# GraphMind

> Memory-grounded AI chat with a personal knowledge graph — built with React, Zustand, React Flow, and Tailwind CSS.

---

## Tech Stack

| Layer        | Technology                                  |
| ------------ | ------------------------------------------- |
| Framework    | React 19 + Vite                             |
| State        | Zustand                                     |
| Graph        | @xyflow/react (React Flow)                  |
| Styling      | Tailwind CSS v4                             |
| Icons        | lucide-react, react-icons                   |

---

## Project Structure

```
frontend/
├── public/
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
│   │   └── useAppStore.js       # Zustand global store
│   ├── hooks/
│   │   └── useGraphHighlight.js # Graph node highlight hook
│   └── data/
│       └── mockData.js          # Mock users, docs, mindmap, chat responses
```

---

## Features

### Core

- **Split-panel layout** — resizable chat + mindmap side-by-side on desktop; tabbed view on mobile.
- **Memory-grounded chat** — AI responses include retrieval time and memory citations that link to graph nodes.
- **Knowledge graph (Mindmap)** — interactive React Flow canvas with zoom, minimap, and node selection.
- **Document ingestion** — modal to add text/URL content; chunks are visualized as new graph nodes.
- **Multi-user switching** — dropdown to switch between demo users; each has isolated docs, graph, and chat.

### Chat Sidebar (New)

- **Collapsible left sidebar** toggled via a button pinned below the navbar.
- **New Chat** — creates a fresh chat session; the previous session is auto-saved.
- **Chat history list** — every conversation is persisted in-memory and displayed with title, message count, and relative timestamp.
- **Pin / Unpin chats** — right-click context menu (three-dot icon) to pin important chats to the top.
- **Delete chat** — remove any chat session from the same context menu.
- **Search** — filter chat history by title.
- **Auto-title** — chat title is derived from the first user message.
- **Mobile-friendly** — overlay backdrop on small screens; content area shifts on desktop.

---

## Getting Started

```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev

# Production build
npm run build
```

---

## Changelog

### 2026-02-20 — Chat Sidebar

**Files added:**
- `src/components/ChatSidebar.jsx` — New sidebar component with full chat history management UI.

**Files modified:**
- `src/store/useAppStore.js` — Added sidebar state (`sidebarOpen`, `toggleSidebar`), chat history state (`chatHistory`, `activeChatId`), and actions (`newChat`, `switchChat`, `pinChat`, `unpinChat`, `deleteChat`). Updated `sendMessage` to auto-create chat sessions and sync messages to history.
- `src/App.jsx` — Imported `ChatSidebar`, added `sidebarOpen` state, content area shifts right when sidebar is open on desktop.
- `src/index.css` — Added `slideInFromLeft` keyframe animation for sidebar entrance.
