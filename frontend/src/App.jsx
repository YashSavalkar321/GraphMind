import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import GraphCanvas from './components/GraphCanvas';
import IngestModal from './components/IngestModal';
import useAppStore from './store/useAppStore';
import { ReactFlowProvider } from '@xyflow/react';

function App() {
  const activeView = useAppStore((s) => s.activeView);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {activeView === 'chat' ? (
          <ChatWindow />
        ) : (
          <ReactFlowProvider>
            <GraphCanvas />
          </ReactFlowProvider>
        )}
      </main>
      <IngestModal />
    </div>
  );
}

export default App;
