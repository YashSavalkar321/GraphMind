import { useState, useRef, useCallback } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { MessageSquare, Network, GripVertical, PanelRightClose, PanelRightOpen } from 'lucide-react';
import Navbar from './components/Navbar';
import ChatWindow from './components/ChatWindow';
import GraphCanvas from './components/GraphCanvas';
import IngestModal from './components/IngestModal';
import Toast from './components/Toast';
import useAppStore from './store/useAppStore';

function App() {
  const activeView = useAppStore((s) => s.activeView);
  const setActiveView = useAppStore((s) => s.setActiveView);

  /* ── Split-pane state (desktop only) ── */
  const [chatPct, setChatPct] = useState(50);          // 20–80 range
  const [graphHidden, setGraphHidden] = useState(false);
  const containerRef = useRef(null);
  const isDragging = useRef(false);

  /* Drag handler for the resize gutter */
  const startDrag = useCallback((e) => {
    e.preventDefault();
    isDragging.current = true;

    const moveHandler = (ev) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const pct = ((clientX - rect.left) / rect.width) * 100;
      setChatPct(Math.min(80, Math.max(20, pct)));
    };
    const upHandler = () => {
      isDragging.current = false;
      document.removeEventListener('mousemove', moveHandler);
      document.removeEventListener('mouseup', upHandler);
      document.removeEventListener('touchmove', moveHandler);
      document.removeEventListener('touchend', upHandler);
    };
    document.addEventListener('mousemove', moveHandler);
    document.addEventListener('mouseup', upHandler);
    document.addEventListener('touchmove', moveHandler);
    document.addEventListener('touchend', upHandler);
  }, []);

  /* Chat width on desktop */
  const chatWidth = graphHidden ? '100%' : `${chatPct}%`;
  const graphWidth = graphHidden ? '0%' : `${100 - chatPct}%`;

  return (
    <div className="h-dvh w-screen flex flex-col overflow-hidden bg-bg">
      {/* ── Top Navbar (60 px) ── */}
      <Navbar />

      {/* ── Mobile tab bar (below lg) ── */}
      <div className="lg:hidden flex border-b border-white/[0.06] bg-surface flex-shrink-0">
        <button
          onClick={() => setActiveView('chat')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-semibold transition-colors cursor-pointer ${
            activeView === 'chat'
              ? 'text-primary-light border-b-2 border-primary bg-primary/5'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Chat
        </button>
        <button
          onClick={() => setActiveView('graph')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-semibold transition-colors cursor-pointer ${
            activeView === 'graph'
              ? 'text-primary-light border-b-2 border-primary bg-primary/5'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <Network className="w-4 h-4" />
          Mindmap
        </button>
      </div>

      {/* ── Main content area ── */}
      <div ref={containerRef} className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        {/* ── Chat panel ── */}
        <style>{`@media(min-width:1024px){.chat-pane{width:${chatWidth} !important;min-width:280px;}}`}</style>
        <div
          className={`chat-pane ${
            activeView === 'chat' ? 'flex' : 'hidden'
          } lg:flex flex-col h-full w-full lg:w-auto transition-[width] duration-150 ease-out`}
        >
          <ChatWindow />
        </div>

        {/* ── Resize gutter (desktop only, hidden when graph collapsed) ── */}
        {!graphHidden && (
          <div
            onMouseDown={startDrag}
            onTouchStart={startDrag}
            className="hidden lg:flex items-center justify-center w-[5px] cursor-col-resize group flex-shrink-0 relative z-20"
            title="Drag to resize panels"
          >
            <div className="w-px h-full bg-white/[0.06] group-hover:bg-primary/40 group-active:bg-primary/60 transition-colors" />
          </div>
        )}

        {/* ── Graph panel ── */}
        <style>{`@media(min-width:1024px){.graph-pane{width:${graphWidth} !important;}}`}</style>
        <div
          className={`graph-pane ${
            activeView === 'graph' ? 'flex' : 'hidden'
          } lg:flex flex-col h-full w-full lg:w-auto transition-[width] duration-150 ease-out overflow-hidden ${graphHidden ? 'lg:!hidden' : ''}`}
        >
          <ReactFlowProvider>
            <GraphCanvas />
          </ReactFlowProvider>
        </div>

        {/* ── Graph toggle button (desktop only) ── */}
        <button
          onClick={() => setGraphHidden(!graphHidden)}
          className="hidden lg:flex absolute top-3 right-3 z-30 items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface/90 border border-white/[0.08] text-[11px] text-text-secondary hover:text-text-primary hover:border-primary/30 transition-all cursor-pointer btn-press backdrop-blur-sm shadow-lg"
          title={graphHidden ? 'Show mindmap' : 'Hide mindmap'}
        >
          {graphHidden ? (
            <>
              <PanelRightOpen className="w-3.5 h-3.5" />
              <span className="font-medium">Show Map</span>
            </>
          ) : (
            <>
              <PanelRightClose className="w-3.5 h-3.5" />
              <span className="font-medium">Hide Map</span>
            </>
          )}
        </button>
      </div>

      {/* Floating layers */}
      <IngestModal />
      <Toast />
    </div>
  );
}

export default App;
