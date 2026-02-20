import { useState, useRef, useEffect } from 'react';
import { Brain, ChevronDown, Check, Upload } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function Navbar() {
  const { users, currentUserId, getCurrentUser, switchUser, openIngestModal } = useAppStore();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);
  const currentUser = getCurrentUser();

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <nav className="h-[60px] flex items-center justify-between px-4 sm:px-6 lg:px-8 border-b border-white/[0.06] bg-surface flex-shrink-0 z-40">
      {/* ── Logo ── */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary via-primary-dark to-accent flex items-center justify-center shadow-lg shadow-primary/30 animate-pulse-glow flex-shrink-0">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div className="hidden sm:block">
          <h1 className="text-[15px] font-extrabold gradient-text leading-none tracking-tight">
            GraphMind
          </h1>
          <p className="text-[10px] text-text-muted font-semibold uppercase tracking-widest mt-0.5">
            Memory Engine
          </p>
        </div>
      </div>

      {/* ── Right side ── */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Ingest button */}
        <button
          onClick={openIngestModal}
          className="group flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-dark hover:from-primary-light hover:to-primary text-white text-sm font-semibold transition-all duration-200 cursor-pointer btn-press shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30"
        >
          <Upload className="w-4 h-4 group-hover:scale-110 transition-transform flex-shrink-0" />
          <span className="hidden sm:inline">Ingest</span>
        </button>

        {/* ── User dropdown ── */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className={`flex items-center gap-2 px-2.5 py-1.5 rounded-xl border transition-all duration-200 cursor-pointer btn-press ${
              showDropdown
                ? 'bg-primary/10 border-primary/25'
                : 'border-transparent hover:bg-white/[0.04]'
            }`}
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ring-2 ring-white/10 shadow-md flex-shrink-0"
              style={{ backgroundColor: currentUser.color }}
            >
              {currentUser.avatar}
            </div>
            <span className="hidden md:inline text-sm font-semibold text-text-primary max-w-[120px] truncate">
              {currentUser.name}
            </span>
            <ChevronDown
              className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 flex-shrink-0 ${
                showDropdown ? 'rotate-180' : ''
              }`}
            />
          </button>

          {/* Dropdown */}
          {showDropdown && (
            <div className="absolute right-0 top-full mt-2 w-56 z-50 bg-surface-light border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 overflow-hidden animate-fade-in-scale">
              <div className="px-4 py-2.5 border-b border-white/[0.06]">
                <p className="text-[10px] font-bold uppercase tracking-widest text-text-muted/60">
                  Current User
                </p>
              </div>
              {users.map((user) => (
                <button
                  key={user.id}
                  onClick={() => {
                    switchUser(user.id);
                    setShowDropdown(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors cursor-pointer border-l-2 ${
                    user.id === currentUserId
                      ? 'bg-primary/8 border-l-primary'
                      : 'border-l-transparent hover:bg-white/[0.04]'
                  }`}
                >
                  <div
                    className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold text-white"
                    style={{ backgroundColor: user.color }}
                  >
                    {user.avatar}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">{user.name}</p>
                    {user.id === currentUserId && (
                      <p className="text-[10px] text-primary-light mt-0.5">Currently active</p>
                    )}
                  </div>
                  {user.id === currentUserId && (
                    <Check className="w-3.5 h-3.5 text-success flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
