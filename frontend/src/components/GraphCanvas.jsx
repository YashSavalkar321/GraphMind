import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, Info, X } from 'lucide-react';
import useAppStore from '../store/useAppStore';

// Custom node component
function MindmapNode({ data, selected }) {
  const colorMap = {
    concept: { bg: '#6366f1', border: '#818cf8', text: '#e0e7ff' },
    entity: { bg: '#8b5cf6', border: '#a78bfa', text: '#ede9fe' },
    document: { bg: '#0ea5e9', border: '#38bdf8', text: '#e0f2fe' },
    fact: { bg: '#10b981', border: '#34d399', text: '#d1fae5' },
  };

  const colors = colorMap[data.nodeType] || colorMap.concept;

  return (
    <div
      className={`px-4 py-2.5 rounded-xl border-2 shadow-lg transition-all duration-200 ${
        selected ? 'scale-110 shadow-2xl' : 'hover:scale-105'
      }`}
      style={{
        backgroundColor: `${colors.bg}20`,
        borderColor: selected ? colors.border : `${colors.bg}60`,
        minWidth: '120px',
        maxWidth: '200px',
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: colors.bg }}
        />
        <span
          className="text-[10px] uppercase tracking-wider font-semibold"
          style={{ color: `${colors.bg}cc` }}
        >
          {data.nodeType}
        </span>
      </div>
      <p className="text-xs font-semibold text-text-primary leading-tight">{data.label}</p>
      {data.description && (
        <p className="text-[10px] text-text-secondary mt-1 leading-snug line-clamp-2">
          {data.description}
        </p>
      )}
    </div>
  );
}

const nodeTypes = { concept: MindmapNode, entity: MindmapNode, document: MindmapNode, fact: MindmapNode };

export default function GraphCanvas() {
  const { getMindmapForCurrentUser, selectedNode, setSelectedNode, getCurrentUser } = useAppStore();
  const currentUser = getCurrentUser();
  const graphData = getMindmapForCurrentUser();

  // Prepare nodes with selection state
  const initialNodes = useMemo(
    () =>
      graphData.nodes.map((n) => ({
        ...n,
        type: n.type || 'concept',
        selected: n.id === selectedNode,
      })),
    [graphData.nodes, selectedNode]
  );

  // Prepare edges with markers
  const initialEdges = useMemo(
    () =>
      graphData.edges.map((e) => ({
        ...e,
        markerEnd: { type: MarkerType.ArrowClosed, color: e.style?.stroke || '#6366f1' },
        labelStyle: { fill: '#a5b4fc', fontSize: 10, fontWeight: 500 },
        labelBgStyle: { fill: '#1e1b4b', fillOpacity: 0.8 },
        labelBgPadding: [4, 2],
        labelBgBorderRadius: 4,
      })),
    [graphData.edges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync when user changes or selectedNode changes
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_, node) => {
      setSelectedNode(node.id === selectedNode ? null : node.id);
    },
    [selectedNode, setSelectedNode]
  );

  // Find selected node data for detail panel
  const selectedNodeData = graphData.nodes.find((n) => n.id === selectedNode);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-lighter bg-surface/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-secondary/20 flex items-center justify-center">
            <Network className="w-5 h-5 text-secondary-light" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-text-primary">Memory Mind Map</h2>
            <p className="text-xs text-text-secondary">
              {graphData.nodes.length} nodes • {graphData.edges.length} edges • {currentUser.name}
            </p>
          </div>
        </div>
        <Legend />
      </div>

      {/* Graph */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#312e81" gap={24} size={1} />
          <Controls position="bottom-left" />
          <MiniMap
            nodeColor={(node) => {
              const map = { concept: '#6366f1', entity: '#8b5cf6', document: '#0ea5e9', fact: '#10b981' };
              return map[node.type] || '#6366f1';
            }}
            maskColor="rgba(15, 10, 46, 0.7)"
            position="bottom-right"
          />
        </ReactFlow>

        {/* Node Detail Panel */}
        {selectedNodeData && (
          <div className="absolute top-4 right-4 w-72 bg-surface border border-surface-lighter rounded-2xl shadow-2xl overflow-hidden animate-fade-in z-10">
            <div className="flex items-center justify-between px-4 py-3 border-b border-surface-lighter">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-primary-light" />
                <span className="text-sm font-semibold text-text-primary">Node Details</span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="w-6 h-6 rounded-lg hover:bg-surface-light flex items-center justify-center transition-colors cursor-pointer"
              >
                <X className="w-3 h-3 text-text-secondary" />
              </button>
            </div>
            <div className="px-4 py-3 space-y-3">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1">ID</p>
                <p className="text-xs font-mono text-text-secondary">{selectedNodeData.id}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1">Label</p>
                <p className="text-sm font-semibold text-text-primary">{selectedNodeData.data.label}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1">Type</p>
                <span className="inline-block px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase bg-primary/20 text-primary-light">
                  {selectedNodeData.data.nodeType}
                </span>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1">Description</p>
                <p className="text-xs text-text-secondary leading-relaxed">{selectedNodeData.data.description}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1">Source</p>
                <p className="text-xs font-mono text-secondary">{selectedNodeData.data.docSource}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Legend() {
  const items = [
    { label: 'Concept', color: '#6366f1' },
    { label: 'Entity', color: '#8b5cf6' },
    { label: 'Document', color: '#0ea5e9' },
    { label: 'Fact', color: '#10b981' },
  ];
  return (
    <div className="flex items-center gap-3">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
          <span className="text-[10px] text-text-secondary font-medium">{item.label}</span>
        </div>
      ))}
    </div>
  );
}
