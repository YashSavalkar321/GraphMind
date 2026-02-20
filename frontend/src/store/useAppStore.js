import { create } from 'zustand';
import {
  USERS,
  INGESTED_DOCS,
  MINDMAP_DATA,
  simulateChatResponse,
  simulateIngest,
} from '../data/mockData';

const useAppStore = create((set, get) => ({
  // ──────────────── Sidebar state ────────────────
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // ──────────────── Chat history state ────────────────
  chatHistory: [],
  activeChatId: null,

  newChat: () => {
    const { messages, activeChatId, chatHistory } = get();
    let updatedHistory = chatHistory;
    // Save current chat if it has messages
    if (activeChatId && messages.length > 0) {
      updatedHistory = chatHistory.map((c) =>
        c.id === activeChatId ? { ...c, messages, updatedAt: new Date().toISOString() } : c,
      );
    }
    const newId = `chat_${Date.now()}`;
    const newSession = {
      id: newId,
      title: 'New Chat',
      messages: [],
      pinned: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    set({
      chatHistory: [newSession, ...updatedHistory],
      activeChatId: newId,
      messages: [],
      isTyping: false,
    });
  },

  switchChat: (chatId) => {
    const { activeChatId, messages, chatHistory } = get();
    if (chatId === activeChatId) return;
    // Save current chat
    const saved = chatHistory.map((c) =>
      c.id === activeChatId ? { ...c, messages, updatedAt: new Date().toISOString() } : c,
    );
    const target = saved.find((c) => c.id === chatId);
    if (!target) return;
    set({
      chatHistory: saved,
      activeChatId: chatId,
      messages: target.messages,
      isTyping: false,
    });
  },

  pinChat: (chatId) =>
    set((s) => ({
      chatHistory: s.chatHistory.map((c) =>
        c.id === chatId ? { ...c, pinned: true } : c,
      ),
    })),

  unpinChat: (chatId) =>
    set((s) => ({
      chatHistory: s.chatHistory.map((c) =>
        c.id === chatId ? { ...c, pinned: false } : c,
      ),
    })),

  deleteChat: (chatId) => {
    const { activeChatId, chatHistory } = get();
    const remaining = chatHistory.filter((c) => c.id !== chatId);
    if (chatId === activeChatId) {
      const next = remaining[0];
      set({
        chatHistory: remaining,
        activeChatId: next?.id || null,
        messages: next?.messages || [],
      });
    } else {
      set({ chatHistory: remaining });
    }
  },

  // ──────────────── User state ────────────────
  users: USERS,
  currentUserId: USERS[0].id,

  getCurrentUser: () => {
    const { users, currentUserId } = get();
    return users.find((u) => u.id === currentUserId) || USERS[0];
  },

  switchUser: (userId) => {
    set({
      currentUserId: userId,
      messages: [],
      isTyping: false,
      selectedNode: null,
      highlightedNodeId: null,
    });
    // ── BACKEND INTEGRATION ──
    // When connected to the real API, trigger a mindmap refetch here:
    // get().fetchMindmap();
  },

  // ──────────────── Documents state ────────────────
  ingestedDocs: { ...INGESTED_DOCS },

  getDocsForCurrentUser: () => {
    const { ingestedDocs, currentUserId } = get();
    return ingestedDocs[currentUserId] || [];
  },

  // ──────────────── Mindmap state ────────────────
  mindmapData: { ...MINDMAP_DATA },

  getMindmapForCurrentUser: () => {
    const { mindmapData, currentUserId } = get();
    return mindmapData[currentUserId] || { nodes: [], edges: [] };
  },

  /**
   * Fetch mindmap from backend.
   * Currently a no-op (mock data is loaded statically).
   */
  fetchMindmap: async () => {
    const { currentUserId } = get();
    // ── BACKEND INTEGRATION ──
    // const res = await fetch(`/api/memory/mindmap?user_id=${currentUserId}`);
    // const data = await res.json();
    // set((s) => ({ mindmapData: { ...s.mindmapData, [currentUserId]: data } }));
  },

  // ──────────────── Node selection & highlight ────────────────
  selectedNode: null,
  setSelectedNode: (nodeId) => set({ selectedNode: nodeId }),

  /**
   * Highlighted node for the "citation click → glow on graph" flow.
   * Auto-clears after 3 s so the glow is temporary.
   */
  highlightedNodeId: null,
  highlightNode: (nodeId) => {
    set({ highlightedNodeId: nodeId, selectedNode: nodeId });
    setTimeout(() => {
      set((s) => (s.highlightedNodeId === nodeId ? { highlightedNodeId: null } : {}));
    }, 3000);
  },

  // ──────────────── Chat state ────────────────
  messages: [],
  isTyping: false,

  sendMessage: async (query) => {
    const { currentUserId, messages, activeChatId, chatHistory } = get();

    // Auto-create a chat session if none exists
    if (!activeChatId) {
      const newId = `chat_${Date.now()}`;
      const newSession = {
        id: newId,
        title: query.slice(0, 40) + (query.length > 40 ? '…' : ''),
        messages: [],
        pinned: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      set({ chatHistory: [newSession, ...chatHistory], activeChatId: newId });
    }

    const userMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };
    const updatedMessages = [...messages, userMessage];
    set({ messages: updatedMessages, isTyping: true });

    // Update chat title from first user message
    const { activeChatId: currentChatId } = get();
    set((s) => ({
      chatHistory: s.chatHistory.map((c) => {
        if (c.id !== currentChatId) return c;
        const isNew = c.title === 'New Chat';
        return {
          ...c,
          messages: updatedMessages,
          updatedAt: new Date().toISOString(),
          ...(isNew ? { title: query.slice(0, 40) + (query.length > 40 ? '…' : '') } : {}),
        };
      }),
    }));

    // Simulate network latency
    await new Promise((r) => setTimeout(r, 300 + Math.random() * 500));

    // ── BACKEND INTEGRATION ──
    // Replace simulateChatResponse with:
    // const res = await fetch('/api/chat', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ user_id: currentUserId, query }),
    // });
    // const data = await res.json();
    const data = simulateChatResponse(currentUserId, query);

    const aiMessage = {
      id: `msg_${Date.now() + 1}`,
      role: 'assistant',
      content: data.response,
      timestamp: new Date().toISOString(),
      retrieval_time_ms: data.retrieval_time_ms,
      memory_citations: data.memory_citations,
    };

    set((s) => {
      const newMessages = [...s.messages, aiMessage];
      return {
        messages: newMessages,
        isTyping: false,
        chatHistory: s.chatHistory.map((c) =>
          c.id === s.activeChatId
            ? { ...c, messages: newMessages, updatedAt: new Date().toISOString() }
            : c,
        ),
      };
    });
  },

  // ──────────────── Ingest state ────────────────
  isIngestModalOpen: false,
  openIngestModal: () => set({ isIngestModalOpen: true }),
  closeIngestModal: () => set({ isIngestModalOpen: false }),
  isIngesting: false,

  ingestDocument: async (title, content, sourceType = 'text') => {
    const { currentUserId } = get();
    set({ isIngesting: true });

    // Simulate network latency
    await new Promise((r) => setTimeout(r, 800 + Math.random() * 1200));

    // ── BACKEND INTEGRATION ──
    // Replace with:
    // const res = await fetch('/api/memory/ingest', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ user_id: currentUserId, text: content, source_type: sourceType }),
    // });
    // const result = await res.json();
    const result = simulateIngest(currentUserId, title, content);

    set((s) => {
      const docs = { ...s.ingestedDocs };
      if (!docs[currentUserId]) docs[currentUserId] = [];
      docs[currentUserId] = [result, ...docs[currentUserId]];
      return {
        ingestedDocs: docs,
        isIngesting: false,
        isIngestModalOpen: false,
      };
    });

    // Show success toast
    get().showToast(`"${title}" ingested — ${result.chunks} chunks, ${result.nodesCreated} nodes`);

    return result;
  },

  // ──────────────── UI state ────────────────
  /** Mobile view tab: 'chat' | 'graph' */
  activeView: 'chat',
  setActiveView: (view) => set({ activeView: view }),

  // ──────────────── Toast ────────────────
  toast: null,
  showToast: (message, type = 'success') => {
    set({ toast: { message, type } });
    setTimeout(() => set({ toast: null }), 4000);
  },
}));

export default useAppStore;
