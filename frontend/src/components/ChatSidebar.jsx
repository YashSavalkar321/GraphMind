import { useState, useRef, useEffect } from 'react';
import {
  Plus,
  Pin,
  PinOff,
  Trash2,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  MoreHorizontal,
  Search,
  History,
} from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function ChatSidebar() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const chatHistory = useAppStore((s) => s.chatHistory);
  const activeChatId = useAppStore((s) => s.activeChatId);
  const newChat = useAppStore((s) => s.newChat);
  const switchChat = useAppStore((s) => s.switchChat);
  const pinChat = useAppStore((s) => s.pinChat);
  const unpinChat = useAppStore((s) => s.unpinChat);
  const deleteChat = useAppStore((s) => s.deleteChat);

  const [search, setSearch] = useState('');
  const [menuOpenId, setMenuOpenId] = useState(null);
  const menuRef = useRef(null);

  // Close context menu on outside click
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpenId(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filtered = chatHistory.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase()),
  );
  const pinned = filtered.filter((c) => c.pinned);
  const unpinned = filtered.filter((c) => !c.pinned);

  const formatDate = (iso) => {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return `${diffDay}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const ChatItem = ({ chat }) => {
    const isActive = chat.id === activeChatId;
    const msgCount = chat.messages.length;
    return (
      <div
        className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150 ${
          isActive
            ? 'bg-gradient-to-r from-primary/15 to-accent/5 border border-primary/30 shadow-[0_0_16px_rgba(99,102,241,0.12)]'
            : 'border border-transparent hover:bg-white/[0.04] hover:border-white/[0.07]'
        }`}
        onClick={() => switchChat(chat.id)}
      >
        {/* Active accent bar */}
        {isActive && (
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-full bg-gradient-to-b from-primary-light to-accent" />
        )}

        {/* Icon */}
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
            isActive
              ? 'bg-primary/20 text-primary-light shadow-[0_0_10px_rgba(99,102,241,0.25)]'
              : 'bg-white/[0.04] text-text-muted group-hover:text-text-secondary'
          }`}
        >
          {chat.pinned ? (
            <Pin className="w-3.5 h-3.5" />
          ) : (
            <MessageSquare className="w-3.5 h-3.5" />
          )}
        </div>

        {/* Text */}
        <div className="flex-1 min-w-0">
          <p
            className={`text-sm font-medium truncate ${
              isActive ? 'text-primary-light' : 'text-text-primary'
            }`}
          >
            {chat.title}
          </p>
          <p className="text-[11px] text-text-muted truncate mt-0.5">
            {msgCount > 0
              ? `${msgCount} message${msgCount > 1 ? 's' : ''} · ${formatDate(chat.updatedAt)}`
              : formatDate(chat.createdAt)}
          </p>
        </div>

        {/* Context menu trigger */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpenId(menuOpenId === chat.id ? null : chat.id);
          }}
          className={`flex-shrink-0 p-1 rounded-md transition-all cursor-pointer ${
            menuOpenId === chat.id
              ? 'opacity-100 bg-white/[0.08]'
              : 'opacity-0 group-hover:opacity-100 hover:bg-white/[0.08]'
          }`}
        >
          <MoreHorizontal className="w-4 h-4 text-text-muted" />
        </button>

        {/* Context menu */}
        {menuOpenId === chat.id && (
          <div
            ref={menuRef}
            className="absolute right-0 top-full mt-1 z-50 w-44 glass-strong rounded-xl overflow-hidden animate-fade-in-scale"
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                chat.pinned ? unpinChat(chat.id) : pinChat(chat.id);
                setMenuOpenId(null);
              }}
              className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors cursor-pointer"
            >
              {chat.pinned ? (
                <>
                  <PinOff className="w-4 h-4" />
                  Unpin Chat
                </>
              ) : (
                <>
                  <Pin className="w-4 h-4" />
                  Pin Chat
                </>
              )}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteChat(chat.id);
                setMenuOpenId(null);
              }}
              className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-danger hover:bg-danger/10 transition-colors cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
              Delete Chat
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Toggle button — always visible */}
      <button
        onClick={toggleSidebar}
        className={`fixed top-[116px] lg:top-[140px] z-50 p-2 rounded-xl glass-panel text-text-muted hover:text-text-primary hover:border-primary/40 transition-all cursor-pointer btn-press ${
          sidebarOpen ? 'left-3 lg:left-[288px]' : 'left-3'
        }`}
        title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {sidebarOpen ? (
          <PanelLeftClose className="w-4 h-4" />
        ) : (
          <PanelLeftOpen className="w-4 h-4" />
        )}
      </button>

      {/* Overlay backdrop on mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`fixed top-[116px] lg:top-[60px] left-0 bottom-0 z-40 w-72 glass border-r border-white/[0.07] flex flex-col transition-transform duration-250 ease-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-white/[0.06] flex-shrink-0">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-primary-light" />
            <h2 className="font-display text-sm font-bold text-text-primary tracking-tight">
              Conversations
            </h2>
            {chatHistory.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-md bg-primary/15 border border-primary/25 text-[10px] font-bold text-primary-light">
                {chatHistory.length}
              </span>
            )}
          </div>
          <button
            onClick={newChat}
            className="sheen flex items-center gap-1.5 px-3 py-1.5 rounded-lg btn-glow text-white text-xs font-semibold cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            New
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-3 flex-shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats…"
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.07] text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-primary/45 focus:bg-white/[0.06] focus:shadow-[0_0_0_3px_rgba(99,102,241,0.1)] transition-all"
            />
          </div>
        </div>

        {/* Chat list */}
        <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-1">
          {/* Pinned section */}
          {pinned.length > 0 && (
            <div className="mb-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-text-muted/60 px-3 mb-2 flex items-center gap-1.5">
                <Pin className="w-3 h-3" />
                Pinned
              </p>
              <div className="space-y-1">
                {pinned.map((chat) => (
                  <ChatItem key={chat.id} chat={chat} />
                ))}
              </div>
            </div>
          )}

          {/* Recent section */}
          {unpinned.length > 0 && (
            <div>
              {pinned.length > 0 && (
                <p className="text-[10px] font-bold uppercase tracking-widest text-text-muted/60 px-3 mb-2">
                  Recent
                </p>
              )}
              <div className="space-y-1">
                {unpinned.map((chat) => (
                  <ChatItem key={chat.id} chat={chat} />
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {chatHistory.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center px-4 py-12">
              <div className="relative w-14 h-14 mb-4">
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/15 to-accent/10 blur-md" />
                <div className="relative w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center">
                  <MessageSquare className="w-6 h-6 text-text-muted/50" />
                </div>
              </div>
              <p className="text-sm text-text-secondary font-medium mb-1">No chats yet</p>
              <p className="text-xs text-text-muted/60 mb-4">
                Start a conversation to see it here
              </p>
              <button
                onClick={newChat}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary/15 border border-primary/30 text-primary-light text-xs font-semibold hover:bg-primary/25 hover:shadow-[0_0_16px_rgba(99,102,241,0.25)] transition-all cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                New Chat
              </button>
            </div>
          )}

          {/* No search results */}
          {chatHistory.length > 0 && filtered.length === 0 && (
            <div className="text-center py-8">
              <p className="text-sm text-text-muted">No matching chats</p>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
