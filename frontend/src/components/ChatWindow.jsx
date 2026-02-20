import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, AlertCircle } from 'lucide-react';
import useAppStore from '../store/useAppStore';
import PerformanceTimer from './PerformanceTimer';
import CitationBadge from './CitationBadge';

export default function ChatWindow() {
  const { messages, isTyping, sendMessage, getCurrentUser } = useAppStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const currentUser = getCurrentUser();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setInput('');
    await sendMessage(trimmed);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Render markdown-like bold
  const renderContent = (text) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="text-primary-light font-semibold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-lighter bg-surface/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-light" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-text-primary">GraphMind Chat</h2>
            <p className="text-xs text-text-secondary">
              Memory-grounded AI • {currentUser.name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="text-xs text-text-secondary">Online</span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {/* Welcome message */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-primary-light" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">Welcome to GraphMind</h3>
            <p className="text-sm text-text-secondary max-w-md leading-relaxed">
              Ask questions about your ingested documents. Every answer is grounded in your personal knowledge graph
              with full memory citations and retrieval metrics.
            </p>
            <div className="flex flex-wrap gap-2 mt-6 justify-center">
              {getSuggestions(currentUser.id).map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                  className="px-3 py-2 rounded-xl bg-surface-light border border-surface-lighter text-xs text-text-secondary hover:text-text-primary hover:border-primary/30 transition-all cursor-pointer"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat messages */}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 animate-fade-in ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-primary/20 flex items-center justify-center mt-1">
                <Bot className="w-4 h-4 text-primary-light" />
              </div>
            )}
            <div
              className={`max-w-[70%] ${
                msg.role === 'user'
                  ? 'bg-primary rounded-2xl rounded-br-md px-4 py-3'
                  : 'bg-surface-light rounded-2xl rounded-bl-md px-4 py-3 border border-surface-lighter'
              }`}
            >
              <p className={`text-sm leading-relaxed ${msg.role === 'user' ? 'text-white' : 'text-text-primary'}`}>
                {msg.role === 'assistant' ? renderContent(msg.content) : msg.content}
              </p>
              {msg.role === 'assistant' && (
                <div className="mt-2 space-y-1">
                  <PerformanceTimer timeMs={msg.retrieval_time_ms} />
                  <CitationBadge citations={msg.memory_citations} />
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div
                className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1 text-[10px] font-bold text-white"
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
            <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-primary/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-primary-light" />
            </div>
            <div className="bg-surface-light rounded-2xl rounded-bl-md px-4 py-3 border border-surface-lighter">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
                <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
                <div className="w-2 h-2 rounded-full bg-primary-light typing-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-surface-lighter bg-surface/50 backdrop-blur-sm">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your memories..."
              rows={1}
              className="w-full px-4 py-3 bg-surface-light border border-surface-lighter rounded-xl text-sm text-text-primary placeholder-text-muted resize-none focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
              style={{ minHeight: '44px', maxHeight: '120px' }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="flex-shrink-0 w-11 h-11 rounded-xl bg-primary hover:bg-primary-light disabled:bg-surface-lighter disabled:cursor-not-allowed flex items-center justify-center transition-all cursor-pointer"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}

function getSuggestions(userId) {
  if (userId === 'user_1') {
    return [
      'What is quantum computing?',
      'Explain neural network architectures',
      'How do graph databases work?',
      'Tell me about cooking recipes',
    ];
  }
  return [
    'What causes climate change?',
    'Explain renewable energy sources',
    'Tell me about quantum physics',
    'How can we reduce CO₂ emissions?',
  ];
}
