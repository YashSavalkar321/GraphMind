import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, Sparkles, MessageCircle, ArrowDown, Zap, Volume2, VolumeX, Square } from 'lucide-react';
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
      // Currently speaking this message → stop
      SpeechHelper.stop();
      setSpeakingMsgId(null);
    } else {
      // Speak this message
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
    <div className="flex flex-col h-full bg-gradient-subtle">
      {/* ── Header ── */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 sm:px-6 py-2.5 border-b border-white/[0.06] bg-surface/80 backdrop-blur-md flex-shrink-0 z-10">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/30 to-accent/20 flex items-center justify-center ring-1 ring-primary/20 flex-shrink-0">
            <Sparkles className="w-5 h-5 text-primary-light" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-bold text-text-primary tracking-tight">Chat</h2>
            <p className="text-[11px] text-text-secondary mt-0.5 truncate">
              Memory-grounded AI &bull; <span className="text-primary-light font-medium">{currentUser?.name || 'Guest'}</span>
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
                ? 'bg-primary/15 border-primary/30 text-primary-light'
                : 'bg-white/[0.03] border-white/[0.08] text-text-muted hover:text-text-secondary hover:border-white/[0.15]'
            }`}
          >
            {ttsEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline text-[11px] font-medium tracking-wide">
              {ttsEnabled ? 'TTS On' : 'TTS Off'}
            </span>
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/10 border border-success/20">
            <div className="w-2 h-2 rounded-full bg-success shadow-sm shadow-success/50 animate-pulse" />
            <span className="text-[11px] text-success font-medium tracking-wide">Online</span>
          </div>
        </div>
      </header>

      {/* ── Messages area ── */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-8 py-8 space-y-8 relative"
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-start min-h-full text-center animate-fade-in py-8">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/10 flex items-center justify-center mb-6 animate-float ring-1 ring-primary/15">
              <Bot className="w-10 h-10 text-primary-light" />
            </div>
            <h3 className="text-xl sm:text-2xl font-bold gradient-text mb-3">Welcome to GraphMind</h3>
            <p className="text-sm text-text-secondary max-w-md leading-relaxed mb-8 px-4">
              Ask questions about your ingested documents. Every answer is grounded in your personal
              knowledge graph with <span className="text-accent font-medium">memory citations</span> and{' '}
              <span className="text-success font-medium">retrieval metrics</span>.
            </p>
            <div className="w-full max-w-lg">
              <p className="text-xs uppercase tracking-widest text-text-muted/70 font-bold mb-4 flex items-center justify-center gap-2">
                <Zap className="w-4 h-4 text-warning" />
                Try asking
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {getSuggestions().map((s, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInput(s);
                      inputRef.current?.focus();
                    }}
                    className="group text-left p-4 rounded-xl bg-surface-light/40 border border-surface-lighter/50 text-sm text-text-secondary hover:text-text-primary hover:border-primary/40 hover:bg-primary/10 transition-all duration-200 cursor-pointer shadow-sm"
                  >
                    <MessageCircle className="w-4 h-4 text-primary/50 group-hover:text-primary-light mb-2 transition-colors" />
                    <span className="leading-snug block">{s}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className={`flex gap-4 ${
              msg.role === 'user' ? 'justify-end animate-slide-in-right' : 'justify-start animate-fade-in'
            }`}
            style={{ animationDelay: `${idx * 30}ms` }}
          >
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary/25 to-accent/15 flex items-center justify-center mt-1 ring-1 ring-primary/20 shadow-md">
                <Bot className="w-5 h-5 text-primary-light" />
              </div>
            )}

            <div className={`max-w-[85%] md:max-w-[75%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              {/* Message bubble */}
              <div
                className={`w-fit ${
                  msg.role === 'user'
                    ? 'bg-surface-lighter/80 border border-surface-lighter rounded-2xl rounded-tr-sm px-5 py-3.5 shadow-md'
                    : 'bg-surface-light rounded-2xl rounded-tl-sm border border-white/[0.08] shadow-lg'
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
                      <span className="inline-block w-[2px] h-[1em] bg-primary-light ml-0.5 animate-pulse align-text-bottom" />
                    )}
                  </p>
                </div>

                {/* Citations & Metrics isolated in a footer section */}
                {msg.role === 'assistant' && !msg.streaming && msg.content && (
                  <div className="bg-white/[0.03] px-5 py-3.5 border-t border-white/[0.06] rounded-b-2xl flex flex-col gap-3 items-start">
                    <div className="flex items-center justify-between w-full">
                      <PerformanceTimer timeMs={msg.retrieval_time_ms} />
                      <button
                        onClick={() => handleSpeak(msg)}
                        title={speakingMsgId === msg.id ? 'Stop speaking' : 'Read aloud'}
                        className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition-all duration-200 cursor-pointer ${
                          speakingMsgId === msg.id
                            ? 'bg-primary/20 text-primary-light border border-primary/30'
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

              {/* Timestamp outside the bubble */}
              <p
                className={`text-[10px] mt-1.5 px-2 ${
                  msg.role === 'user' ? 'text-text-muted/50 text-right' : 'text-text-muted/50 pl-6'
                }`}
              >
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>

            {msg.role === 'user' && (
              <div
                className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center mt-1 text-sm font-bold text-white shadow-md ring-2 ring-surface"
                style={{ backgroundColor: currentUser?.color || '#6366f1' }}
              >
                {currentUser?.avatar || 'U'}
              </div>
            )}
          </div>
        ))}

        {isTyping && (
          <div className="flex gap-4 animate-fade-in">
            <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary/25 to-accent/15 flex items-center justify-center ring-1 ring-primary/20">
              <Bot className="w-5 h-5 text-primary-light" />
            </div>
            <div className="bg-surface-light rounded-2xl rounded-tl-sm px-6 py-4 border border-white/[0.08] shadow-lg w-24 flex items-center justify-center">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
                <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
                <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} className="h-4" />
      </div>

      {/* ── Input Area ── */}
      <footer className="px-4 sm:px-6 pt-4 pb-6 bg-surface border-t border-surface-lighter/30 flex-shrink-0 z-10">
        <div className="max-w-4xl mx-auto relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your memories..."
            rows={1}
            className="w-full bg-surface-light/50 border border-surface-lighter/50 rounded-2xl pl-5 pr-14 py-3.5 text-sm text-text-primary placeholder-text-muted/60 resize-none focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all leading-relaxed"
            style={{ minHeight: '48px', maxHeight: '150px' }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
            }}
          />
          {charCount > 0 && (
            <span className="absolute right-14 bottom-3 text-[10px] text-text-muted/40 font-mono">
              {charCount}
            </span>
          )}
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="absolute right-2.5 bottom-2 mb-2 w-9 h-9 flex items-center justify-center rounded-xl bg-primary hover:bg-primary-light disabled:bg-surface-lighter disabled:opacity-40 disabled:cursor-not-allowed text-white transition-all cursor-pointer"
          >
            <Send className=" w-4 h-4" />
          </button>
        </div>
      </footer>
    </div>
  );
}

function getSuggestions() {
  return [
    'What do you know about me so far?',
    'Summarize my ingested documents',
    'What topics are in my knowledge graph?',
    'Find connections between my notes',
  ];
}