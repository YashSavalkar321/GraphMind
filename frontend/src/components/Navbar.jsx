import { useState, useRef, useEffect } from 'react';
import { Brain, ChevronDown, Check, Upload, LogOut, LogIn, UserPlus } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function Navbar() {
  const users = useAppStore((s) => s.users);
  const currentUserId = useAppStore((s) => s.currentUserId);
  const switchUser = useAppStore((s) => s.switchUser);
  const openIngestModal = useAppStore((s) => s.openIngestModal);
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  const authUser = useAppStore((s) => s.authUser);
  const logout = useAppStore((s) => s.logout);
  const currentUser = useAppStore((s) => s.getCurrentUser());
  
  const [showDropdown, setShowDropdown] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'signup'
  const dropdownRef = useRef(null);

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
    <nav className="h-[60px] flex items-center justify-between px-6 sm:px-8 lg:px-10 border-b border-white/[0.06] bg-surface flex-shrink-0 z-40">
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
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Ingest button */}
        <button
          onClick={openIngestModal}
          className="group flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary-light text-white text-sm font-medium transition-all duration-200 cursor-pointer btn-press shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/30"
        >
          <Upload className="w-4 h-4 flex-shrink-0" />
          <span className="hidden sm:inline">Ingest</span>
        </button>

        {/* ── Auth-aware user area ── */}
        {isAuthenticated ? (
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
                style={{ backgroundColor: currentUser?.color || '#6366f1' }}
              >
                {currentUser?.avatar || 'U'}
              </div>
              <span className="hidden md:inline text-sm font-semibold text-text-primary max-w-[120px] truncate">
                {currentUser?.name || 'Guest'}
              </span>
              <ChevronDown
                className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 flex-shrink-0 ${
                  showDropdown ? 'rotate-180' : ''
                }`}
              />
            </button>

            {showDropdown && (
              <div className="absolute right-0 top-full mt-2 w-56 z-50 bg-surface-light border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 overflow-hidden animate-fade-in-scale">
                <div className="px-4 py-2.5 border-b border-white/[0.06]">
                  <p className="text-xs font-semibold text-text-primary truncate">{authUser?.name}</p>
                  <p className="text-[10px] text-text-muted truncate">{authUser?.email}</p>
                </div>
                <button
                  onClick={() => { logout(); setShowDropdown(false); }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-red-400 hover:bg-white/[0.04] transition-colors cursor-pointer"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setAuthMode('login'); setShowAuthModal(true); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium text-text-primary hover:bg-white/[0.04] transition-colors cursor-pointer"
            >
              <LogIn className="w-4 h-4" />
              <span className="hidden sm:inline">Login</span>
            </button>
            <button
              onClick={() => { setAuthMode('signup'); setShowAuthModal(true); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary hover:bg-primary-light text-white text-sm font-medium transition-all duration-200 cursor-pointer btn-press"
            >
              <UserPlus className="w-4 h-4" />
              <span className="hidden sm:inline">Sign Up</span>
            </button>
          </div>
        )}

        {/* ── Legacy user dropdown (only when not authenticated) ── */}
        {!isAuthenticated && (
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
        )}
      </div>

      {/* ── Auth Modal ── */}
      {showAuthModal && (
        <AuthModal
          mode={authMode}
          setMode={setAuthMode}
          onClose={() => setShowAuthModal(false)}
        />
      )}
    </nav>
  );
}


// ── Auth Modal (inline) ──
function AuthModal({ mode, setMode, onClose }) {
  const signup = useAppStore((s) => s.signup);
  const login = useAppStore((s) => s.login);
  const authLoading = useAppStore((s) => s.authLoading);
  const authError = useAppStore((s) => s.authError);
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Close automatically on successful auth
  useEffect(() => {
    if (isAuthenticated) onClose();
  }, [isAuthenticated, onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (mode === 'signup') {
      await signup(name, email, password);
    } else {
      await login(email, password);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-light border border-white/[0.08] rounded-2xl w-full max-w-sm mx-4 p-6 shadow-2xl animate-fade-in-scale">
        <h2 className="text-lg font-bold text-text-primary mb-4">
          {mode === 'signup' ? 'Create Account' : 'Welcome Back'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          {mode === 'signup' && (
            <input
              type="text"
              placeholder="Full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-xl bg-surface border border-white/[0.08] text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary/50"
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-3 py-2 rounded-xl bg-surface border border-white/[0.08] text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary/50"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full px-3 py-2 rounded-xl bg-surface border border-white/[0.08] text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary/50"
          />

          {authError && (
            <p className="text-xs text-red-400">{authError}</p>
          )}

          <button
            type="submit"
            disabled={authLoading}
            className="w-full py-2 rounded-xl bg-primary hover:bg-primary-light text-white text-sm font-semibold transition-all disabled:opacity-50 cursor-pointer"
          >
            {authLoading ? 'Please wait…' : mode === 'signup' ? 'Sign Up' : 'Login'}
          </button>
        </form>

        <p className="text-xs text-text-muted mt-4 text-center">
          {mode === 'signup' ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}
            className="text-primary hover:underline cursor-pointer"
          >
            {mode === 'signup' ? 'Login' : 'Sign Up'}
          </button>
        </p>

        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-text-muted hover:text-text-primary text-lg cursor-pointer"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
