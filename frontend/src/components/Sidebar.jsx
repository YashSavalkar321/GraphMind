import { useState, useRef } from 'react';
import {
  Brain,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Network,
  FileText,
  Plus,
  User,
  Check,
  Clock,
  LogOut,
} from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function Sidebar() {
  const {
    users,
    currentUserId,
    getCurrentUser,
    switchUser,
    getDocsForCurrentUser,
    activeView,
    setActiveView,
    sidebarCollapsed,
    toggleSidebar,
    openIngestModal,
  } = useAppStore();

  const [showUserMenu, setShowUserMenu] = useState(false);
  const currentUser = getCurrentUser();
  const docs = getDocsForCurrentUser();

  return (
    <aside
      className={`relative flex flex-col bg-surface border-r border-surface-lighter transition-all duration-300 ${
        sidebarCollapsed ? 'w-[68px]' : 'w-[280px]'
      }`}
    >
      {/* Logo / Brand */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-surface-lighter">
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-primary flex items-center justify-center animate-pulse-glow">
          <Brain className="w-5 h-5 text-white" />
        </div>
        {!sidebarCollapsed && (
          <div className="animate-fade-in">
            <h1 className="text-lg font-bold text-text-primary tracking-tight">GraphMind</h1>
            <p className="text-[10px] text-text-muted font-medium uppercase tracking-widest">Memory Engine</p>
          </div>
        )}
      </div>

      {/* User Switcher */}
      <div className="relative px-3 py-3 border-b border-surface-lighter">
        <button
          onClick={() => setShowUserMenu(!showUserMenu)}
          className="w-full flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-surface-light transition-colors cursor-pointer"
        >
          <div
            className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
            style={{ backgroundColor: currentUser.color }}
          >
            {currentUser.avatar}
          </div>
          {!sidebarCollapsed && (
            <div className="flex-1 text-left animate-fade-in">
              <p className="text-sm font-semibold text-text-primary truncate">{currentUser.name}</p>
              <p className="text-[10px] text-text-secondary">Active Session</p>
            </div>
          )}
        </button>

        {/* Dropdown */}
        {showUserMenu && !sidebarCollapsed && (
          <div className="absolute left-3 right-3 top-full mt-1 z-50 bg-surface-light border border-surface-lighter rounded-xl shadow-2xl overflow-hidden animate-fade-in">
            <div className="px-3 py-2 border-b border-surface-lighter">
              <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">Switch User</p>
            </div>
            {users.map((user) => (
              <button
                key={user.id}
                onClick={() => {
                  switchUser(user.id);
                  setShowUserMenu(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 hover:bg-surface-lighter transition-colors cursor-pointer ${
                  user.id === currentUserId ? 'bg-surface-lighter/50' : ''
                }`}
              >
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
                  style={{ backgroundColor: user.color }}
                >
                  {user.avatar}
                </div>
                <span className="text-sm text-text-primary flex-1 text-left">{user.name}</span>
                {user.id === currentUserId && <Check className="w-4 h-4 text-success" />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="px-3 py-3 space-y-1">
        <NavItem
          icon={MessageSquare}
          label="Chat"
          active={activeView === 'chat'}
          collapsed={sidebarCollapsed}
          onClick={() => setActiveView('chat')}
        />
        <NavItem
          icon={Network}
          label="Mind Map"
          active={activeView === 'graph'}
          collapsed={sidebarCollapsed}
          onClick={() => setActiveView('graph')}
        />
      </nav>

      {/* Ingest Button */}
      <div className="px-3 py-2">
        <button
          onClick={openIngestModal}
          className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-primary hover:bg-primary-light text-white font-medium text-sm transition-all cursor-pointer ${
            sidebarCollapsed ? 'px-2' : 'px-4'
          }`}
        >
          <Plus className="w-4 h-4" />
          {!sidebarCollapsed && <span>Ingest Document</span>}
        </button>
      </div>

      {/* Ingested Documents List */}
      {!sidebarCollapsed && (
        <div className="flex-1 overflow-y-auto px-3 py-3 animate-fade-in">
          <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-2 px-2">
            Ingested Documents ({docs.length})
          </p>
          <div className="space-y-1">
            {docs.map((doc, i) => (
              <div
                key={doc.id}
                className="flex items-start gap-2.5 px-2 py-2 rounded-lg hover:bg-surface-light transition-colors group animate-slide-in"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <FileText className="w-4 h-4 text-secondary mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-text-primary truncate">{doc.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-text-secondary">{doc.chunks} chunks</span>
                    <span className="text-[10px] text-text-muted">•</span>
                    <span className="text-[10px] text-text-secondary">
                      {new Date(doc.ingestedAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collapse Toggle */}
      <div className="mt-auto border-t border-surface-lighter px-3 py-3">
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg hover:bg-surface-light transition-colors text-text-secondary hover:text-text-primary cursor-pointer"
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!sidebarCollapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>
    </aside>
  );
}

function NavItem({ icon: Icon, label, active, collapsed, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all cursor-pointer ${
        active
          ? 'bg-primary/20 text-primary-light border border-primary/30'
          : 'text-text-secondary hover:bg-surface-light hover:text-text-primary border border-transparent'
      }`}
    >
      <Icon className={`w-[18px] h-[18px] flex-shrink-0 ${active ? 'text-primary-light' : ''}`} />
      {!collapsed && <span className="text-sm font-medium">{label}</span>}
    </button>
  );
}
