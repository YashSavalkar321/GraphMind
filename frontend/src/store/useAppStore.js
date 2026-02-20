import { create } from 'zustand';
import { USERS, INGESTED_DOCS, MINDMAP_DATA, simulateChatResponse, simulateIngest } from '../data/mockData';

const useAppStore = create((set, get) => ({
  // ---- User state ----
  users: USERS,
  currentUserId: USERS[0].id,
  getCurrentUser: () => {
    const state = get();
    return state.users.find((u) => u.id === state.currentUserId) || USERS[0];
  },
  switchUser: (userId) => {
    set({
      currentUserId: userId,
      messages: [],
      isTyping: false,
      selectedNode: null,
    });
  },

  // ---- Documents state ----
  ingestedDocs: { ...INGESTED_DOCS },
  getDocsForCurrentUser: () => {
    const state = get();
    return state.ingestedDocs[state.currentUserId] || [];
  },

  // ---- Mindmap state ----
  mindmapData: { ...MINDMAP_DATA },
  getMindmapForCurrentUser: () => {
    const state = get();
    return state.mindmapData[state.currentUserId] || { nodes: [], edges: [] };
  },
  selectedNode: null,
  setSelectedNode: (node) => set({ selectedNode: node }),

  // ---- Chat state ----
  messages: [],
  isTyping: false,

  sendMessage: async (query) => {
    const { currentUserId, messages } = get();

    // Add user message
    const userMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    set({ messages: [...messages, userMessage], isTyping: true });

    // Simulate network delay (300-800ms)
    await new Promise((resolve) => setTimeout(resolve, 300 + Math.random() * 500));

    // Get mock response
    // --- BACKEND INTEGRATION ---
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

    set((state) => ({
      messages: [...state.messages, aiMessage],
      isTyping: false,
    }));
  },

  // ---- Ingest state ----
  isIngestModalOpen: false,
  openIngestModal: () => set({ isIngestModalOpen: true }),
  closeIngestModal: () => set({ isIngestModalOpen: false }),
  isIngesting: false,

  ingestDocument: async (title, content) => {
    const { currentUserId } = get();
    set({ isIngesting: true });

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 800 + Math.random() * 1200));

    // --- BACKEND INTEGRATION ---
    // Replace simulateIngest with:
    // const res = await fetch('/api/memory/ingest', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ user_id: currentUserId, title, content }),
    // });
    // const result = await res.json();
    const result = simulateIngest(currentUserId, title, content);

    set((state) => {
      const docs = { ...state.ingestedDocs };
      if (!docs[currentUserId]) docs[currentUserId] = [];
      docs[currentUserId] = [result, ...docs[currentUserId]];
      return {
        ingestedDocs: docs,
        isIngesting: false,
        isIngestModalOpen: false,
      };
    });

    return result;
  },

  // ---- UI state ----
  activeView: 'chat', // 'chat' | 'graph'
  setActiveView: (view) => set({ activeView: view }),
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}));

export default useAppStore;
