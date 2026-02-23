import { create } from 'zustand';
import {
  simulateChatResponse,
  simulateIngest,
} from '../data/mockData';

// ── API base path (Vite proxy: /api → http://localhost:8000) ──
const API = '/api';

// ── JWT helpers ──
const getStoredAuth = () => {
  try {
    const token = localStorage.getItem('gm_token');
    const user = JSON.parse(localStorage.getItem('gm_user') || 'null');
    if (user && !user.id) {
      user.id = user.user_id;
      user.avatar = user.name?.[0]?.toUpperCase() || 'U';
      user.color = '#6366f1';
    }
    return token && user ? { token, user } : null;
  } catch {
    return null;
  }
};

const storeAuth = (token, user) => {
  localStorage.setItem('gm_token', token);
  localStorage.setItem('gm_user', JSON.stringify(user));
};

const clearAuth = () => {
  localStorage.removeItem('gm_token');
  localStorage.removeItem('gm_user');
};

const authHeaders = () => {
  const token = localStorage.getItem('gm_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const storedAuth = getStoredAuth();

const EMPTY_MINDMAP = { nodes: [], edges: [] };
const EMPTY_DOCS = [];

const useAppStore = create((set, get) => ({
  // ──────────────── Auth state ────────────────
  isAuthenticated: !!storedAuth,
  authUser: storedAuth?.user || null,
  authLoading: false,
  authError: null,

  signup: async (name, email, password) => {
    set({ authLoading: true, authError: null });
    try {
      const res = await fetch(`${API}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Signup failed' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      const user = { 
        user_id: data.user_id, 
        name: data.name, 
        email: data.email,
        id: data.user_id,
        avatar: data.name[0]?.toUpperCase() || 'U',
        color: '#6366f1'
      };
      storeAuth(data.token, user);
      set({
        isAuthenticated: true,
        authUser: user,
        currentUserId: data.user_id,
        authLoading: false,
      });
      get().fetchMindmap();
      get().fetchChats();
    } catch (err) {
      set({ authLoading: false, authError: err.message });
    }
  },

  login: async (email, password) => {
    set({ authLoading: true, authError: null });
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      const user = { 
        user_id: data.user_id, 
        name: data.name, 
        email: data.email,
        id: data.user_id,
        avatar: data.name[0]?.toUpperCase() || 'U',
        color: '#6366f1'
      };
      storeAuth(data.token, user);
      set({
        isAuthenticated: true,
        authUser: user,
        currentUserId: data.user_id,
        authLoading: false,
      });
      get().fetchMindmap();
      get().fetchChats();
    } catch (err) {
      set({ authLoading: false, authError: err.message });
    }
  },

  logout: () => {
    clearAuth();
    set({
      isAuthenticated: false,
      authUser: null,
      currentUserId: null,
      messages: [],
      chatHistory: [],
      activeChatId: null,
      selectedNode: null,
      highlightedNodeId: null,
    });
  },

  // ──────────────── Sidebar state ────────────────
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // ──────────────── Chat history state ────────────────
  chatHistory: [],
  activeChatId: null,

  /**
   * Fetch all chat sessions from backend (called after login/signup).
   */
  fetchChats: async () => {
    try {
      const res = await fetch(`${API}/chats`, {
        headers: { ...authHeaders() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const sessions = await res.json();
      const mapped = sessions.map((s) => ({
        id: s.chat_id,
        title: s.title,
        messages: s.messages || [],
        pinned: s.pinned || false,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
      }));
      // If there are persisted chats, load the most recent one
      if (mapped.length > 0) {
        set({
          chatHistory: mapped,
          activeChatId: mapped[0].id,
          messages: mapped[0].messages || [],
        });
      } else {
        set({ chatHistory: [], activeChatId: null, messages: [] });
      }
    } catch (err) {
      console.warn('fetchChats: API unavailable', err.message);
    }
  },

  /**
   * Persist a chat session to backend (fire-and-forget).
   */
  _saveChat: (chatSession) => {
    if (!chatSession || !chatSession.id) return;
    fetch(`${API}/chats`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        chat_id: chatSession.id,
        title: chatSession.title || 'New Chat',
        pinned: chatSession.pinned || false,
        messages: chatSession.messages || [],
        createdAt: chatSession.createdAt || new Date().toISOString(),
        updatedAt: chatSession.updatedAt || new Date().toISOString(),
      }),
    }).catch((err) => console.warn('_saveChat failed:', err.message));
  },

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

  pinChat: (chatId) => {
    set((s) => ({
      chatHistory: s.chatHistory.map((c) =>
        c.id === chatId ? { ...c, pinned: true } : c,
      ),
    }));
    const chat = get().chatHistory.find((c) => c.id === chatId);
    if (chat) get()._saveChat(chat);
  },

  unpinChat: (chatId) => {
    set((s) => ({
      chatHistory: s.chatHistory.map((c) =>
        c.id === chatId ? { ...c, pinned: false } : c,
      ),
    }));
    const chat = get().chatHistory.find((c) => c.id === chatId);
    if (chat) get()._saveChat(chat);
  },

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
    // Delete from backend
    fetch(`${API}/chats/${chatId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    }).catch((err) => console.warn('deleteChat backend failed:', err.message));
  },

  // ──────────────── User state ────────────────
  users: [],
  currentUserId: storedAuth?.user?.user_id || null,

  getCurrentUser: () => {
    const { authUser, isAuthenticated } = get();
    if (isAuthenticated && authUser) {
      return authUser;
    }
    return null;
  },

  switchUser: (userId) => {
    set({
      currentUserId: userId,
      messages: [],
      isTyping: false,
      selectedNode: null,
      highlightedNodeId: null,
    });
    // Fetch mindmap from backend for the new user
    get().fetchMindmap();
  },

  // ──────────────── Documents state ────────────────
  ingestedDocs: {},

  getDocsForCurrentUser: () => {
    const { ingestedDocs, currentUserId } = get();
    return ingestedDocs[currentUserId] || EMPTY_DOCS;
  },

  // ──────────────── Mindmap state ────────────────
  mindmapData: {},

  getMindmapForCurrentUser: () => {
    const { mindmapData, currentUserId } = get();
    const data = mindmapData[currentUserId];
    return data && Array.isArray(data.nodes) && Array.isArray(data.edges) 
      ? data 
      : EMPTY_MINDMAP;
  },

  /**
   * Fetch mindmap from backend.
   * Falls back to local mock data if the API is unreachable.
   */
  fetchMindmap: async () => {
    const { currentUserId } = get();
    if (!currentUserId) return;
    try {
      const res = await fetch(`${API}/memory/mindmap?user_id=${currentUserId}`, {
        headers: { ...authHeaders() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set((s) => ({ mindmapData: { ...s.mindmapData, [currentUserId]: data } }));
    } catch (err) {
      console.warn('fetchMindmap: API unavailable, using local data', err.message);
    }
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

  /**
   * Retrieval subgraph focus — shows the nodes used to answer a query.
   * Pass an array of node IDs (from memory_citations). Switches to graph view.
   */
  retrievalFocusNodeIds: null,   // null = off, Set<string> = active
  focusRetrievalNodes: (nodeIds) => {
    if (!nodeIds || nodeIds.length === 0) return;
    set({ retrievalFocusNodeIds: new Set(nodeIds), activeView: 'graph' });
  },
  clearRetrievalFocus: () => set({ retrievalFocusNodeIds: null }),

  // ──────────────── Text-to-Speech state ────────────────
  ttsEnabled: JSON.parse(localStorage.getItem('gm_tts_enabled') || 'false'),
  toggleTts: () =>
    set((s) => {
      const next = !s.ttsEnabled;
      localStorage.setItem('gm_tts_enabled', JSON.stringify(next));
      return { ttsEnabled: next };
    }),

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

    // ── Call backend with SSE streaming (fall back to non-stream, then mock) ──
    const aiMsgId = `msg_${Date.now() + 1}`;
    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ user_id: currentUserId, query }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Add empty AI message bubble immediately
      const aiMessage = {
        id: aiMsgId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        retrieval_time_ms: null,
        memory_citations: [],
        broad_query: false,
        streaming: true,
      };
      set((s) => ({ messages: [...s.messages, aiMessage], isTyping: false }));

      // Read SSE stream
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const payload = JSON.parse(line.slice(6));

            if (payload.token) {
              // Append token to the AI message
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === aiMsgId ? { ...m, content: m.content + payload.token } : m,
                ),
              }));
            } else if (payload.done) {
              // Final metadata event — attach citations & perf
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === aiMsgId
                    ? {
                        ...m,
                        streaming: false,
                        retrieval_time_ms: payload.retrieval_time_ms,
                        memory_citations: payload.memory_citations,
                        broad_query: payload.broad_query ?? false,
                      }
                    : m,
                ),
              }));
            } else if (payload.error) {
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === aiMsgId
                    ? { ...m, content: m.content || 'Sorry, an error occurred.', streaming: false }
                    : m,
                ),
              }));
            }
          } catch {
            // skip malformed JSON lines
          }
        }
      }

      // Sync final state to chat history & persist to backend
      set((s) => ({
        chatHistory: s.chatHistory.map((c) =>
          c.id === s.activeChatId
            ? { ...c, messages: s.messages, updatedAt: new Date().toISOString() }
            : c,
        ),
      }));
      const activeChat = get().chatHistory.find((c) => c.id === get().activeChatId);
      if (activeChat) get()._saveChat(activeChat);
      // Refresh mindmap — ingest already ran server-side before streaming started
      get().fetchMindmap();
    } catch (err) {
      console.warn('stream API unavailable, falling back:', err.message);

      // Fallback: try non-streaming /chat, then mock
      let data;
      try {
        const res2 = await fetch(`${API}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          body: JSON.stringify({ user_id: currentUserId, query }),
        });
        if (!res2.ok) throw new Error(`HTTP ${res2.status}`);
        data = await res2.json();
      } catch {
        await new Promise((r) => setTimeout(r, 300 + Math.random() * 500));
        data = simulateChatResponse(currentUserId, query);
      }

      const aiMessage = {
        id: aiMsgId,
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        retrieval_time_ms: data.retrieval_time_ms,
        memory_citations: data.memory_citations,
        broad_query: data.broad_query ?? false,
      };
      set((s) => {
        const newMessages = [...s.messages.filter((m) => m.id !== aiMsgId), aiMessage];
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
      // Persist fallback chat to backend too
      const activeChat = get().chatHistory.find((c) => c.id === get().activeChatId);
      if (activeChat) get()._saveChat(activeChat);      // Refresh mindmap after fallback response
      get().fetchMindmap();    }
  },

  // ──────────────── Ingest state ────────────────
  isIngestModalOpen: false,
  openIngestModal: () => set({ isIngestModalOpen: true }),
  closeIngestModal: () => set({ isIngestModalOpen: false }),
  isIngesting: false,

  ingestDocument: async (title, content, sourceType = 'text') => {
    const { currentUserId } = get();
    set({ isIngesting: true });

    // ── Call backend (fall back to mock if offline) ──
    let result;
    try {
      const res = await fetch(`${API}/memory/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ user_id: currentUserId, text: content, source_type: sourceType, title }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      result = await res.json();
    } catch (err) {
      console.warn('ingest API unavailable, using mock:', err.message);
      await new Promise((r) => setTimeout(r, 800 + Math.random() * 1200));
      result = simulateIngest(currentUserId, title, content);
    }

    // Normalize: ensure ingestedAt is present
    if (!result.ingestedAt) result.ingestedAt = new Date().toISOString();

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

    // Refresh mindmap with newly created nodes
    get().fetchMindmap();

    return result;
  },

  /**
   * Upload a binary file (PDF, TXT, MD) to the /upload endpoint.
   * The backend extracts text (PyPDF2 for PDFs) and ingests into the graph.
   */
  uploadFile: async (file) => {
    const { currentUserId } = get();
    set({ isIngesting: true });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API}/upload`, {
        method: 'POST',
        headers: { ...authHeaders() },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const result = await res.json();

      const title = file.name.replace(/\.[^.]+$/, '');
      const doc = {
        id: `doc_${Date.now()}`,
        title,
        type: 'file',
        chunks: result.chunks_processed || 1,
        nodesCreated: result.entities_created || 0,
        edgesCreated: result.facts_created || 0,
        ingestedAt: new Date().toISOString(),
      };

      set((s) => {
        const docs = { ...s.ingestedDocs };
        if (!docs[currentUserId]) docs[currentUserId] = [];
        docs[currentUserId] = [doc, ...docs[currentUserId]];
        return {
          ingestedDocs: docs,
          isIngesting: false,
          isIngestModalOpen: false,
        };
      });

      get().showToast(
        `"${title}" uploaded — ${doc.chunks} chunks, ${doc.nodesCreated} nodes`,
      );
      get().fetchMindmap();

      return doc;
    } catch (err) {
      set({ isIngesting: false });
      throw err;
    }
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

// Auto-refresh graph and chat history from backend when app loads with persisted session
if (storedAuth) {
  setTimeout(() => {
    useAppStore.getState().fetchMindmap();
    useAppStore.getState().fetchChats();
  }, 150);
}

export default useAppStore;
