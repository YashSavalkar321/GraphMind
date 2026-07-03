import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Bot,
  Sparkles,
  ArrowDown,
  Zap,
  Volume2,
  VolumeX,
  Square,
  BrainCircuit,
  Bookmark,
  UserRound,
  FileText,
  Network,
  GitBranch,
  CornerDownLeft,
} from 'lucide-react';
import useAppStore from '../store/useAppStore';
import PerformanceTimer from './PerformanceTimer';
import CitationBadge from './CitationBadge';
import SpeechHelper from '../utils/speechHelper';

export default function ChatWindow() {
  const messages = useAppStore((s) => s.messages);
  const isTyping = useAppStore((s) => s.isTyping);
  const sendMessage = useAppStore((s) => s.sendMessage);
  const currentUser = useAppStore((s) => s.getCurrentUser());
  const ttsEnabled = useAppStore((s) => s.ttsEnabled);
  const toggleTts = useAppStore((s) => s.toggleTts);

  const [input, setInput] = useState('');
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState(null);
  const messagesEndRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const inputRef = useRef(null);
  const lastSpokenMsgId = useRef(null);

  // Preload TTS voices on mount
  useEffect(() => {
    SpeechHelper.preloadVoices();
  }, []);

  // Auto-speak new assistant responses when TTS is enabled
  useEffect(() => {
    if (!ttsEnabled || messages.length === 0) return;
    const lastMsg = messages[messages.length - 1];
    if (
      lastMsg.role === 'assistant' &&
      !lastMsg.streaming &&
      lastMsg.content &&
      lastMsg.id !== lastSpokenMsgId.current
    ) {
      lastSpokenMsgId.current = lastMsg.id;
      setSpeakingMsgId(lastMsg.id);
      SpeechHelper.speak(lastMsg.content, {
        onEnd: () => setSpeakingMsgId(null),
        onError: () => setSpeakingMsgId(null),
      });
    }
  }, [messages, ttsEnabled]);

  // Stop speech when TTS is toggled off
  useEffect(() => {
    if (!ttsEnabled) {
      SpeechHelper.stop();
      setSpeakingMsgId(null);
    }
  }, [ttsEnabled]);

  const handleSpeak = useCallback((msg) => {
    if (speakingMsgId === msg.id) {
      SpeechHelper.stop();
      setSpeakingMsgId(null);
    } else {
      setSpeakingMsgId(msg.id);
      SpeechHelper.speak(msg.content, {
        onEnd: () => setSpeakingMsgId(null),
        onError: () => setSpeakingMsgId(null),
      });
    }
  }, [speakingMsgId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [currentUser?.id]);

  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > 200);
  };

  const scrollToBottom = () =>
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

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

  const renderContent = (text) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={i} className="text-secondary-light font-semibold">
          {part.slice(2, -2)}
        </strong>
      ) : (
        <span key={i}>{part}</span>
      ),
    );
  };

  const charCount = input.length;

  return (
    <div className="flex flex-col h-full bg-gradient-subtle relative">
      {/* ── Header ── */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 sm:px-6 py-2.5 border-b border-white/[0.06] glass flex-shrink-0 z-10">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary/30 via-accent/20 to-transparent flex items-center justify-center ring-1 ring-primary/25 flex-shrink-0 shadow-[0_0_18px_rgba(99,102,241,0.25)]">
            <Sparkles className="w-5 h-5 text-primary-light" />
          </div>
          <div className="min-w-0">
            <h2 className="font-display text-base font-bold text-text-primary tracking-tight">Chat</h2>
            <p className="text-[11px] text-text-secondary mt-0.5 truncate">
              Memory-grounded AI &bull;{' '}
              <span className="text-primary-light font-medium">{currentUser?.name || 'Guest'}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0 self-start sm:self-auto">
          {/* TTS toggle */}
          <button
            onClick={toggleTts}
            title={ttsEnabled ? 'Disable auto-speak' : 'Enable auto-speak'}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border transition-all duration-200 cursor-pointer ${
              ttsEnabled
                ? 'bg-primary/15 border-primary/35 text-primary-light shadow-[0_0_14px_rgba(99,102,241,0.25)]'
                : 'bg-white/[0.03] border-white/[0.08] text-text-muted hover:text-text-secondary hover:border-white/[0.15]'
            }`}
          >
            {ttsEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline text-[11px] font-medium tracking-wide">
              {ttsEnabled ? 'TTS On' : 'TTS Off'}
            </span>
          </button>
          {/* Live status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/10 border border-success/25 shadow-[0_0_14px_rgba(52,211,153,0.15)]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
            </span>
            <span className="text-[11px] text-success font-semibold tracking-wide">Online</span>
          </div>
        </div>
      </header>

      {/* ── Messages area ── */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-8 py-8 space-y-7 relative"
      >
        {messages.length === 0 && <WelcomeHero onPick={(s) => { setInput(s); inputRef.current?.focus(); }} />}

        {/* Message list */}
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 16, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 28 }}
            className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && <AssistantAvatar speaking={speakingMsgId === msg.id} />}

            <div className={`max-w-[85%] md:max-w-[75%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              {/* Message bubble */}
              <div
                className={`w-fit overflow-hidden ${
                  msg.role === 'user'
                    ? 'bubble-user rounded-3xl rounded-tr-md px-5 py-3.5'
                    : 'bubble-assistant rounded-3xl rounded-tl-md'
                }`}
              >
                <div className={msg.role === 'assistant' ? 'px-5 pt-4 pb-3' : ''}>
                  <p
                    className={`text-[14px] sm:text-[15px] leading-[1.75] break-words ${
                      msg.role === 'user' ? 'text-white' : 'text-text-primary'
                    }`}
                  >
                    {msg.role === 'assistant' ? renderContent(msg.content) : msg.content}
                    {msg.role === 'assistant' && msg.streaming && (
                      <span className="inline-block w-[2.5px] h-[1.05em] rounded-full bg-gradient-to-b from-primary-light to-accent-light ml-1 animate-pulse align-text-bottom" />
                    )}
                  </p>
                </div>

                {/* Citations & metrics footer */}
                {msg.role === 'assistant' && !msg.streaming && msg.content && (
                  <div className="bg-white/[0.025] px-5 py-3.5 border-t border-white/[0.06] flex flex-col gap-3 items-start">
                    <div className="flex items-center justify-between w-full gap-3">
                      <PerformanceTimer timeMs={msg.retrieval_time_ms} />
                      <button
                        onClick={() => handleSpeak(msg)}
                        title={speakingMsgId === msg.id ? 'Stop speaking' : 'Read aloud'}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all duration-200 cursor-pointer ${
                          speakingMsgId === msg.id
                            ? 'bg-primary/20 text-primary-light border border-primary/35 shadow-[0_0_12px_rgba(99,102,241,0.3)]'
                            : 'bg-white/[0.04] text-text-muted hover:text-text-secondary hover:bg-white/[0.08] border border-transparent'
                        }`}
                      >
                        {speakingMsgId === msg.id ? (
                          <><Square className="w-3 h-3" /> Stop</>
                        ) : (
                          <><Volume2 className="w-3 h-3" /> Speak</>
                        )}
                      </button>
                    </div>
                    <CitationBadge citations={msg.memory_citations} broadQuery={msg.broad_query} />
                  </div>
                )}
              </div>

              {/* Timestamp */}
              <p
                className={`text-[10px] mt-1.5 px-2 text-text-muted/50 ${
                  msg.role === 'user' ? 'text-right' : 'pl-4'
                }`}
              >
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>

            {msg.role === 'user' && (
              <div
                className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center mt-1 text-[13px] font-bold text-white shadow-[0_4px_16px_rgba(99,102,241,0.35)] ring-2 ring-white/15 bg-gradient-to-br from-indigo-500 to-violet-600"
                style={currentUser?.color ? { background: `linear-gradient(135deg, ${currentUser.color}, #8b5cf6)` } : undefined}
              >
                {currentUser?.avatar || 'U'}
              </div>
            )}
          </motion.div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-3.5"
          >
            <AssistantAvatar thinking />
            <div className="bubble-assistant rounded-3xl rounded-tl-md px-6 py-4 flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-gradient-to-br from-primary-light to-accent-light typing-dot" />
                <div className="w-2 h-2 rounded-full bg-gradient-to-br from-primary-light to-accent-light typing-dot" />
                <div className="w-2 h-2 rounded-full bg-gradient-to-br from-primary-light to-accent-light typing-dot" />
              </div>
              <span className="text-[11px] text-text-muted font-medium">searching memory…</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} className="h-4" />
      </div>

      {/* Scroll-to-bottom */}
      <AnimatePresence>
        {showScrollBtn && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 8 }}
            onClick={scrollToBottom}
            className="absolute bottom-32 left-1/2 -translate-x-1/2 z-20 w-9 h-9 rounded-full glass-panel flex items-center justify-center text-text-secondary hover:text-text-primary hover:border-primary/40 cursor-pointer"
            title="Scroll to bottom"
          >
            <ArrowDown className="w-4 h-4" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* ── Input: floating command bar ── */}
      <footer className="px-4 sm:px-6 pt-2 pb-4 flex-shrink-0 z-10">
        <div className="max-w-4xl mx-auto">
          <div className="command-bar rounded-3xl flex items-end gap-2 pl-5 pr-2.5 py-2.5">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your memories…"
              rows={1}
              className="flex-1 bg-transparent border-none text-sm text-text-primary placeholder-text-muted/60 resize-none focus:outline-none leading-relaxed py-1.5"
              style={{ minHeight: '32px', maxHeight: '150px' }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
              }}
            />
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className="w-10 h-10 flex-shrink-0 flex items-center justify-center rounded-2xl btn-glow text-white cursor-pointer"
              title="Send (Enter)"
            >
              <Send className="w-4 h-4" />
            </motion.button>
          </div>
          <div className="flex items-center justify-between px-3 mt-2">
            <p className="text-[10px] text-text-muted/60 flex items-center gap-1.5">
              <CornerDownLeft className="w-3 h-3" />
              <span><span className="text-text-muted font-semibold">Enter</span> to send &bull; <span className="text-text-muted font-semibold">Shift+Enter</span> for newline</span>
            </p>
            {charCount > 0 && (
              <span className="text-[10px] text-text-muted/50 font-mono">{charCount} chars</span>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ── Assistant avatar with glow ── */
function AssistantAvatar({ thinking = false, speaking = false }) {
  return (
    <div className="relative flex-shrink-0 w-10 h-10 mt-1">
      {(thinking || speaking) && <div className="pulse-ring" />}
      <div
        className={`w-10 h-10 rounded-2xl bg-gradient-to-br from-primary/35 via-accent/25 to-secondary/15 flex items-center justify-center ring-1 ring-primary/30 shadow-[0_0_18px_rgba(99,102,241,0.3)] ${
          thinking ? 'animate-breathe' : ''
        }`}
      >
        <Bot className="w-5 h-5 text-primary-light" />
      </div>
    </div>
  );
}

/* ── Welcome hero (empty state) ── */
const SUGGESTIONS = [
  { text: 'What do you know about me so far?', icon: UserRound,  hue: 'from-indigo-500/25 to-indigo-500/5',  ring: 'ring-indigo-400/30',  iconColor: 'text-indigo-300' },
  { text: 'Summarize my ingested documents',   icon: FileText,   hue: 'from-violet-500/25 to-violet-500/5',  ring: 'ring-violet-400/30',  iconColor: 'text-violet-300' },
  { text: 'What topics are in my knowledge graph?', icon: Network, hue: 'from-cyan-500/25 to-cyan-500/5',    ring: 'ring-cyan-400/30',    iconColor: 'text-cyan-300' },
  { text: 'Find connections between my notes', icon: GitBranch,  hue: 'from-fuchsia-500/25 to-fuchsia-500/5', ring: 'ring-fuchsia-400/30', iconColor: 'text-fuchsia-300' },
];

const FEATURES = [
  { icon: BrainCircuit, label: 'Graph RAG' },
  { icon: Zap,          label: '<15 ms retrieval' },
  { icon: Bookmark,     label: 'Cited answers' },
];

function WelcomeHero({ onPick }) {
  return (
    <div className="flex flex-col min-h-full">
      <div className="m-auto w-full flex flex-col items-center text-center py-6">
      {/* Orb */}
      <motion.div
        initial={{ opacity: 0, scale: 0.7 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        className="relative w-24 h-24 mb-7"
      >
        <div className="absolute inset-[-16px] rounded-full bg-gradient-to-br from-primary/30 via-accent/20 to-secondary/20 blur-2xl animate-breathe" />
        <div className="pulse-ring" />
        <div className="pulse-ring pulse-ring-delayed" />
        <div className="orb-ring" />
        <div className="absolute inset-[5px] rounded-full bg-[#0a0d1d]/90 backdrop-blur flex items-center justify-center">
          <BrainCircuit className="w-11 h-11 text-primary-light animate-float" strokeWidth={1.5} />
        </div>
      </motion.div>

      {/* Headline */}
      <motion.h3
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        className="font-display text-3xl sm:text-4xl font-bold hero-gradient-text mb-3 tracking-tight px-4"
      >
        Your memory, alive.
      </motion.h3>

      <motion.p
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.16 }}
        className="text-sm text-text-secondary max-w-md leading-relaxed mb-5 px-4"
      >
        Ask anything about what you've taught me. Every answer is grounded in your
        personal knowledge graph — with{' '}
        <span className="text-accent-light font-medium">memory citations</span> and{' '}
        <span className="text-success font-medium">retrieval metrics</span>.
      </motion.p>

      {/* Feature chips */}
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.24 }}
        className="flex flex-wrap items-center justify-center gap-2 mb-8 px-4"
      >
        {FEATURES.map(({ icon: Icon, label }) => (
          <div
            key={label}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] text-[11px] font-medium text-text-secondary"
          >
            <Icon className="w-3.5 h-3.5 text-primary-light" />
            {label}
          </div>
        ))}
      </motion.div>

      {/* Suggestions */}
      <div className="w-full max-w-xl px-2">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-[10px] uppercase tracking-[0.28em] text-text-muted/70 font-bold mb-4 flex items-center justify-center gap-2"
        >
          <Zap className="w-3.5 h-3.5 text-warning" />
          Try asking
        </motion.p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {SUGGESTIONS.map(({ text, icon: Icon, hue, ring, iconColor }, i) => (
            <motion.button
              key={text}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.34 + i * 0.07, type: 'spring', stiffness: 260, damping: 22 }}
              whileHover={{ y: -3 }}
              onClick={() => onPick(text)}
              className="sheen group text-left p-4 rounded-2xl glass-panel hover:border-primary/35 transition-colors duration-200 cursor-pointer"
            >
              <div
                className={`w-8 h-8 rounded-xl bg-gradient-to-br ${hue} ring-1 ${ring} flex items-center justify-center mb-2.5 group-hover:scale-110 transition-transform`}
              >
                <Icon className={`w-4 h-4 ${iconColor}`} />
              </div>
              <span className="leading-snug block text-[13px] text-text-secondary group-hover:text-text-primary transition-colors">
                {text}
              </span>
            </motion.button>
          ))}
        </div>
      </div>
      </div>
    </div>
  );
}
