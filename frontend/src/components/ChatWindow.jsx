import { useState, useRef, useEffect } from 'react';
import { Send, Bot, Sparkles, MessageCircle, ArrowDown, Zap } from 'lucide-react';
import useAppStore from '../store/useAppStore';
import PerformanceTimer from './PerformanceTimer';
import CitationBadge from './CitationBadge';

export default function ChatWindow() {
  const { messages, isTyping, sendMessage, getCurrentUser } = useAppStore();
  const [input, setInput] = useState('');
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const messagesEndRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const inputRef = useRef(null);
  const currentUser = getCurrentUser();

  /* Auto-scroll on new messages */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  /* Focus input on mount & user switch */
  useEffect(() => {
    inputRef.current?.focus();
  }, [currentUser.id]);

  /* Track scroll to toggle scroll-to-bottom fab */
  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > 200);
  };

  const scrollToBottom = () =>
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  /* Send logic */
  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isTyping) return;
    setInput('');
    if (inputRef.current) inputRef.current.style.height = 'auto';
    await sendMessage(trimmed);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* Render markdown-style bold */
  const renderContent = (text) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={i} className="text-primary-light font-semibold">
          {part.slice(2, -2)}
        </strong>
      ) : (
        <span key={i}>{part}</span>
      ),
    );
  };

  const charCount = input.length;

  return (
    <div className="flex flex-col h-full bg-gradient-subtle">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-3.5 border-b border-white/[0.06] bg-surface/60 backdrop-blur-md flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/30 to-accent/20 flex items-center justify-center ring-1 ring-primary/20 flex-shrink-0">
            <Sparkles className="w-4 h-4 text-primary-light" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-text-primary tracking-tight">Chat</h2>
            <p className="text-[10px] text-text-secondary mt-0.5 truncate">
              Memory-grounded AI &bull;{' '}
              <span className="text-primary-light font-medium">{currentUser.name}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-success/8 border border-success/15 flex-shrink-0">
          <div className="w-1.5 h-1.5 rounded-full bg-success shadow-sm shadow-success/50 animate-pulse" />
          <span className="text-[10px] text-success font-medium">Online</span>
        </div>
      </header>

      {/* ── Messages area (internal scroll) ── */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden px-6 py-6 space-y-5 relative"
      >
        {/* Empty / welcome state */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in py-6">
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/10 flex items-center justify-center mb-5 animate-float ring-1 ring-primary/15">
              <Bot className="w-8 h-8 sm:w-10 sm:h-10 text-primary-light" />
            </div>
            <h3 className="text-lg sm:text-xl font-bold gradient-text mb-2">Welcome to GraphMind</h3>
            <p className="text-xs sm:text-sm text-text-secondary max-w-md leading-relaxed mb-6 px-2">
              Ask questions about your ingested documents. Every answer is grounded in your personal
              knowledge graph with{' '}
              <span className="text-accent font-medium">memory citations</span> and{' '}
              <span className="text-success font-medium">retrieval metrics</span>.
            </p>
            <div className="w-full max-w-sm">
              <p className="text-[10px] uppercase tracking-widest text-text-muted/60 font-semibold mb-3">
                <Zap className="w-3 h-3 inline-block mr-1 -mt-0.5" />
                Try asking
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {getSuggestions(currentUser.id).map((s, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInput(s);
                      inputRef.current?.focus();
                    }}
                    className="group text-left px-4 py-3.5 rounded-xl bg-surface-light/40 border border-surface-lighter/40 text-xs text-text-secondary hover:text-text-primary hover:border-primary/30 hover:bg-primary/5 transition-all duration-200 cursor-pointer btn-press"
                  >
                    <MessageCircle className="w-3.5 h-3.5 text-text-muted/40 group-hover:text-primary-light mb-1.5 transition-colors" />
                    <span className="leading-relaxed break-words">{s}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Message list ── */}
        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${
              msg.role === 'user'
                ? 'justify-end animate-slide-in-right'
                : 'justify-start animate-fade-in'
            }`}
            style={{ animationDelay: `${idx * 30}ms` }}
          >
            {/* Bot avatar */}
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-primary/25 to-accent/15 flex items-center justify-center mt-1 ring-1 ring-primary/15">
                <Bot className="w-4 h-4 text-primary-light" />
              </div>
            )}

            {/* Bubble */}
            <div
              className={`max-w-[92%] sm:max-w-[88%] lg:max-w-[90%] flex-wrap overflow-hidden ${
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-primary to-primary-dark rounded-2xl rounded-br-md px-5 py-3.5 shadow-lg shadow-primary/15'
                  : 'bg-surface-light/70 backdrop-blur-sm rounded-2xl rounded-bl-md px-5 py-3.5 border border-surface-lighter/40 shadow-sm'
              }`}
            >
              <p
                className={`text-[13px] sm:text-sm leading-[1.75] break-words ${
                  msg.role === 'user' ? 'text-white' : 'text-text-primary'
                }`}
              >
                {msg.role === 'assistant' ? renderContent(msg.content) : msg.content}
              </p>

              {/* ── Metrics + Citations (mandatory for every assistant message) ── */}
              {msg.role === 'assistant' && (
                <div className="mt-3 pt-3 border-t border-surface-lighter/30 space-y-2.5 flex-wrap">
                  <PerformanceTimer timeMs={msg.retrieval_time_ms} />
                  <CitationBadge citations={msg.memory_citations} />
                </div>
              )}

              {/* Timestamp */}
              <p
                className={`text-[10px] mt-2.5 ${
                  msg.role === 'user' ? 'text-white/50 text-right' : 'text-text-muted/50'
                }`}
              >
                {new Date(msg.timestamp).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>

            {/* User avatar */}
            {msg.role === 'user' && (
              <div
                className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1 text-[11px] font-bold text-white shadow-md ring-2 ring-white/10"
                style={{ backgroundColor: currentUser.color }}
              >
                {currentUser.avatar}
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex gap-3 animate-fade-in">
            <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-primary/25 to-accent/15 flex items-center justify-center ring-1 ring-primary/15">
              <Bot className="w-4 h-4 text-primary-light" />
            </div>
            <div className="bg-surface-light/70 backdrop-blur-sm rounded-2xl rounded-bl-md px-5 py-3.5 border border-surface-lighter/40">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
                  <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
                  <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
                </div>
                <span className="text-[10px] text-text-muted/50 ml-2">Thinking…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Scroll-to-bottom FAB */}
      {showScrollBtn && (
        <div className="absolute bottom-28 right-6 z-10">
          <button
            onClick={scrollToBottom}
            className="w-8 h-8 rounded-full bg-surface-light border border-surface-lighter/50 shadow-lg flex items-center justify-center hover:bg-primary/20 hover:border-primary/30 transition-all cursor-pointer btn-press animate-fade-in"
          >
            <ArrowDown className="w-3.5 h-3.5 text-text-secondary" />
          </button>
        </div>
      )}

      {/* ── Input (sticky bottom, keyboard-safe) ── */}
      <footer className="px-6 py-4 border-t border-white/[0.06] bg-surface/60 backdrop-blur-md flex-shrink-0 pb-[env(safe-area-inset-bottom,16px)]">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your memories…"
              rows={1}
              className="w-full pl-4 pr-14 py-2.5 bg-surface-light/60 border border-surface-lighter/50 rounded-2xl text-sm text-text-primary placeholder-text-muted/50 resize-none focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15 focus:bg-surface-light/80 transition-all duration-200 leading-[1.6]"
              style={{ minHeight: '44px', maxHeight: '120px' }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
            />
            {charCount > 0 && (
              <span className="absolute right-4 bottom-3.5 text-[10px] text-text-muted/30 font-mono">
                {charCount}
              </span>
            )}
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="flex-shrink-0 w-11 h-11 rounded-2xl bg-gradient-to-br from-primary to-primary-dark hover:from-primary-light hover:to-primary disabled:from-surface-lighter disabled:to-surface-lighter disabled:cursor-not-allowed flex items-center justify-center transition-all duration-200 cursor-pointer btn-press shadow-lg shadow-primary/20 disabled:shadow-none"
            title="Send message (Enter)"
          >
            <Send
              className={`w-4 h-4 text-white transition-transform ${
                input.trim() ? 'translate-x-0.5 -translate-y-0.5' : ''
              }`}
            />
          </button>
        </div>
        <p className="text-[10px] text-text-muted/30 mt-2 pl-1 hidden sm:block">
          Press{' '}
          <kbd className="px-1.5 py-0.5 rounded bg-surface-lighter/20 text-text-muted/40 font-mono text-[9px]">
            Enter
          </kbd>{' '}
          to send &bull;{' '}
          <kbd className="px-1.5 py-0.5 rounded bg-surface-lighter/20 text-text-muted/40 font-mono text-[9px]">
            Shift+Enter
          </kbd>{' '}
          for new line
        </p>
      </footer>
    </div>
  );
}

/* ── Suggestion bubbles per user ── */
function getSuggestions(userId) {
  if (userId === 'user_1') {
    return [
      'What is quantum computing?',
      'Explain neural network architectures',
      'How do graph databases work?',
      'Tell me about knowledge graphs',
    ];
  }
  return [
    'What causes climate change?',
    'Explain renewable energy sources',
    'Tell me about energy storage',
    'How can we reduce CO₂ emissions?',
  ];
}
