import { useState, useRef, useCallback, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { MessageSquare, Network, PanelRightClose, PanelRightOpen } from 'lucide-react';
import Navbar from './components/Navbar';
import ChatSidebar from './components/ChatSidebar';
import ChatWindow from './components/ChatWindow';
import GraphCanvas from './components/GraphCanvas';
import IngestModal from './components/IngestModal';
import Toast from './components/Toast';
import useAppStore from './store/useAppStore';

function App() {
  const activeView = useAppStore((s) => s.activeView);
  const setActiveView = useAppStore((s) => s.setActiveView);
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);

  const [chatPct, setChatPct] = useState(40); // Better default split
  const [graphHidden, setGraphHidden] = useState(false);
  const containerRef = useRef(null);
  const isDragging = useRef(false);
  const lastXRef = useRef(0);

  const startDrag = useCallback((e) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.userSelect = 'none'; // Prevent text selection while dragging
    lastXRef.current = e.touches ? e.touches[0].clientX : e.clientX;

    const moveHandler = (ev) => {
      if (!isDragging.current || !containerRef.current) return;
      const currentX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const delta = currentX - lastXRef.current;
      const rect = containerRef.current.getBoundingClientRect();
      const change = (delta / rect.width) * 100;
      setChatPct((prev) => Math.min(80, Math.max(20, prev + change)));
      lastXRef.current = currentX; // Update for next move
    };

    const upHandler = () => {
      isDragging.current = false;
      document.body.style.userSelect = '';
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

  const chatWidth = graphHidden ? '100%' : `${chatPct}%`;
  const graphWidth = graphHidden ? '0%' : `${100 - chatPct}%`;

  return (
    <div className="h-dvh w-screen flex flex-col overflow-hidden bg-bg">
      <Navbar />
      <ChatSidebar />

      {/* Mobile Tabs: Added border-transparent to inactive state to prevent layout shift */}
      <div className="lg:hidden flex border-b border-white/[0.06] bg-surface flex-shrink-0 z-20">
        <button
          onClick={() => setActiveView('chat')}
          className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-semibold transition-all cursor-pointer border-b-2 ${
            activeView === 'chat'
              ? 'text-primary-light border-primary bg-primary/5'
              : 'text-text-muted border-transparent hover:text-text-primary hover:bg-white/[0.02]'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Chat
        </button>
        <button
          onClick={() => setActiveView('graph')}
          className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-semibold transition-all cursor-pointer border-b-2 ${
            activeView === 'graph'
              ? 'text-primary-light border-primary bg-primary/5'
              : 'text-text-muted border-transparent hover:text-text-primary hover:bg-white/[0.02]'
          }`}
        >
          <Network className="w-4 h-4" />
          Mindmap
        </button>
      </div>

      <div
        ref={containerRef}
        className={`flex-1 flex flex-col lg:flex-row overflow-hidden relative transition-[margin] duration-250 ease-out ${
          sidebarOpen ? 'lg:ml-72' : 'lg:ml-0'
        }`}
      >
        {/* Chat Panel */}
        <style>{`@media(min-width:1024px){.chat-pane{width:${chatWidth} !important;min-width:320px;}}`}</style>
        <div
          className={`chat-pane ${
            activeView === 'chat' ? 'flex' : 'hidden'
          } lg:flex flex-col h-full w-full lg:w-auto transition-[width] duration-150 ease-out z-10`}
        >
          <ChatWindow />
        </div>

        {/* Resize Gutter: Wider invisible hit-area (w-4) with a visual 1px line */}
        {!graphHidden && (
          <div
            onMouseDown={startDrag}
            onTouchStart={startDrag}
            className="hidden lg:flex items-center justify-center w-4 -ml-2 -mr-2 cursor-col-resize group flex-shrink-0 relative z-30"
            title="Drag to resize panels"
          >
            <div className="w-[1px] h-full bg-white/[0.06] group-hover:bg-primary/50 group-active:bg-primary transition-colors shadow-[0_0_10px_rgba(0,0,0,0.5)]" />
          </div>
        )}

        {/* Graph Panel */}
        <style>{`@media(min-width:1024px){.graph-pane{width:${graphWidth} !important;}}`}</style>
        <div
          className={`graph-pane ${
            activeView === 'graph' ? 'flex' : 'hidden'
          } lg:flex flex-col h-full w-full lg:w-auto transition-[width] duration-150 ease-out overflow-hidden relative ${
            graphHidden ? 'lg:!hidden' : ''
          }`}
        >
          <ReactFlowProvider>
            <GraphCanvas />
          </ReactFlowProvider>
        </div>

        {/* Graph Toggle Button: Always visible outside the graph panel */}
        <button
          onClick={() => setGraphHidden(!graphHidden)}
          className="hidden lg:flex absolute top-32 right-4 z-[60] items-center justify-center p-2 rounded-lg bg-surface/90 border border-white/[0.08] text-text-muted hover:text-text-primary hover:border-primary/40 transition-all cursor-pointer backdrop-blur-md shadow-xl btn-press"
        >
          {graphHidden ? (
            <>
              <PanelRightOpen className="w-4 h-4" />
              <span className="font-semibold"></span>
            </>
          ) : (
            <>
              <PanelRightClose className="w-4 h-4" />
              <span className="font-semibold"></span>
            </>
          )}
        </button>
      </div>

      <IngestModal />
      <Toast />
    </div>
  );
}

export default App;