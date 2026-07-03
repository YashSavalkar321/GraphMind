import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  ChevronDown,
  Upload,
  LogOut,
  LogIn,
  UserPlus,
  Mail,
  Lock,
  User,
  Loader2,
  Sparkles,
  X,
  AlertCircle,
} from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function Navbar() {
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
    <nav className="h-[60px] flex items-center justify-between px-4 sm:px-8 lg:px-10 border-b border-white/[0.07] glass flex-shrink-0 z-40 relative">
      {/* Bottom hairline gradient */}
      <div className="absolute bottom-[-1px] left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary/40 to-transparent pointer-events-none" />

      {/* ── Logo ── */}
      <div className="flex items-center gap-3">
        <div className="relative w-10 h-10 flex-shrink-0">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary/50 via-accent/40 to-secondary/30 blur-md animate-breathe" />
          <div className="orb-ring" />
          <div className="absolute inset-[3px] rounded-full bg-[#0a0d1d] flex items-center justify-center">
            <Brain className="w-[18px] h-[18px] text-primary-light" />
          </div>
        </div>
        <div className="hidden sm:block">
          <h1 className="font-display text-[17px] font-bold text-shimmer leading-none tracking-tight">
            GraphMind
          </h1>
          <p className="text-[9.5px] text-text-muted font-semibold uppercase tracking-[0.22em] mt-1">
            Neural Memory Engine
          </p>
        </div>
      </div>

      {/* ── Right side ── */}
      <div className="flex items-center gap-2.5 sm:gap-4">
        {/* Ingest button */}
        <button
          onClick={openIngestModal}
          className="sheen flex items-center justify-center gap-2 px-4 py-2 rounded-xl btn-glow text-white text-sm font-semibold cursor-pointer"
        >
          <Upload className="w-4 h-4 flex-shrink-0" />
          <span className="hidden sm:inline">Ingest</span>
        </button>

        {/* ── Auth-aware user area ── */}
        {isAuthenticated ? (
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className={`flex items-center gap-2 pl-1.5 pr-2.5 py-1.5 rounded-2xl border transition-all duration-200 cursor-pointer btn-press ${
                showDropdown
                  ? 'bg-primary/10 border-primary/30'
                  : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/[0.12]'
              }`}
            >
              <div className="relative">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shadow-lg flex-shrink-0 bg-gradient-to-br from-indigo-500 to-violet-600 ring-1 ring-white/20"
                  style={currentUser?.color ? { background: `linear-gradient(135deg, ${currentUser.color}, #8b5cf6)` } : undefined}
                >
                  {currentUser?.avatar || 'U'}
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-success border-2 border-[#0a0d1d]" />
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

            <AnimatePresence>
              {showDropdown && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  transition={{ duration: 0.16, ease: 'easeOut' }}
                  className="absolute right-0 top-full mt-2 w-60 z-50 glass-strong rounded-2xl overflow-hidden"
                >
                  <div className="px-4 py-3.5 border-b border-white/[0.07] bg-gradient-to-r from-primary/10 to-transparent">
                    <p className="text-sm font-bold text-text-primary truncate">{authUser?.name}</p>
                    <p className="text-[11px] text-text-muted truncate mt-0.5">{authUser?.email}</p>
                  </div>
                  <button
                    onClick={() => { logout(); setShowDropdown(false); }}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm font-medium text-danger hover:bg-danger/10 transition-colors cursor-pointer"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setAuthMode('login'); setShowAuthModal(true); }}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium text-text-secondary border border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.05] hover:text-text-primary hover:border-white/[0.14] transition-all cursor-pointer btn-press"
            >
              <LogIn className="w-4 h-4" />
              <span className="hidden sm:inline">Login</span>
            </button>
            <button
              onClick={() => { setAuthMode('signup'); setShowAuthModal(true); }}
              className="sheen flex items-center gap-1.5 px-4 py-2 rounded-xl btn-glow text-white text-sm font-semibold cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              <span className="hidden sm:inline">Sign Up</span>
            </button>
          </div>
        )}
      </div>

      {/* ── Auth Modal (portal — the nav's backdrop-filter would otherwise
             trap position:fixed inside the 60px navbar) ── */}
      {createPortal(
        <AnimatePresence>
          {showAuthModal && (
            <AuthModal
              mode={authMode}
              setMode={setAuthMode}
              onClose={() => setShowAuthModal(false)}
            />
          )}
        </AnimatePresence>,
        document.body,
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

  const inputClass =
    'w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text-primary placeholder-text-muted/60 focus:outline-none focus:border-primary/50 focus:bg-white/[0.06] focus:shadow-[0_0_0_3px_rgba(99,102,241,0.12)] transition-all';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-md p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ type: 'spring', stiffness: 320, damping: 26 }}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-sm gradient-border glass-strong rounded-3xl p-7 overflow-hidden"
      >
        {/* Ambient glow inside the card */}
        <div className="absolute -top-16 -right-16 w-48 h-48 rounded-full bg-primary/20 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-16 w-48 h-48 rounded-full bg-accent/15 blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="relative flex flex-col items-center text-center mb-6">
          <div className="relative w-14 h-14 mb-4">
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary/50 to-accent/40 blur-lg animate-breathe" />
            <div className="orb-ring" />
            <div className="absolute inset-[3px] rounded-full bg-[#0a0d1d] flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-primary-light" />
            </div>
          </div>
          <h2 className="font-display text-xl font-bold hero-gradient-text">
            {mode === 'signup' ? 'Create your memory' : 'Welcome back'}
          </h2>
          <p className="text-xs text-text-muted mt-1.5">
            {mode === 'signup'
              ? 'Your personal knowledge graph starts here'
              : 'Your knowledge graph missed you'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="relative space-y-3">
          {mode === 'signup' && (
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                type="text"
                placeholder="Full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className={inputClass}
              />
            </div>
          )}
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={inputClass}
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className={inputClass}
            />
          </div>

          {authError && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-danger/10 border border-danger/25"
            >
              <AlertCircle className="w-4 h-4 text-danger flex-shrink-0" />
              <p className="text-xs text-danger font-medium">{authError}</p>
            </motion.div>
          )}

          <button
            type="submit"
            disabled={authLoading}
            className="w-full py-2.5 rounded-xl btn-glow text-white text-sm font-bold cursor-pointer flex items-center justify-center gap-2"
          >
            {authLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Please wait…
              </>
            ) : mode === 'signup' ? (
              'Create Account'
            ) : (
              'Login'
            )}
          </button>
        </form>

        <p className="relative text-xs text-text-muted mt-5 text-center">
          {mode === 'signup' ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}
            className="text-primary-light font-semibold hover:text-accent-light transition-colors cursor-pointer"
          >
            {mode === 'signup' ? 'Login' : 'Sign Up'}
          </button>
        </p>

        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 rounded-xl flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-white/[0.06] transition-all cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </motion.div>
    </motion.div>
  );
}
