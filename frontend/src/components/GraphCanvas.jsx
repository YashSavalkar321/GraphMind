import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  useReactFlow,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, Info, X, GitBranch, CircleDot, MousePointerClick } from 'lucide-react';
import useAppStore from '../store/useAppStore';
import useGraphHighlight from '../hooks/useGraphHighlight';

/* ── Colour palette per node type ── */
const COLOR_MAP = {
  concept:  { bg: '#6366f1', border: '#818cf8', glow: 'rgba(99,102,241,0.35)'  },
  entity:   { bg: '#8b5cf6', border: '#a78bfa', glow: 'rgba(139,92,246,0.35)'  },
  document: { bg: '#0ea5e9', border: '#38bdf8', glow: 'rgba(14,165,233,0.35)'  },
  fact:     { bg: '#10b981', border: '#34d399', glow: 'rgba(16,185,129,0.35)'  },
};

/* ── Custom Node ── */
function MindmapNode({ id, data, selected }) {
  const highlightedNodeId = useAppStore((s) => s.highlightedNodeId);
  const isHighlighted = id === highlightedNodeId;
  const colors = COLOR_MAP[data.nodeType] || COLOR_MAP.concept;

  return (
    <div
      className={`relative flex flex-col h-auto w-auto rounded-xl border-2 shadow-lg transition-all duration-300 overflow-hidden ${
        selected || isHighlighted
          ? 'scale-110 shadow-2xl ring-1'
          : 'hover:scale-105 hover:shadow-xl'
      }`}
      style={{
        backgroundColor: '#1e293b',
        borderColor: selected || isHighlighted ? colors.border : `${colors.bg}40`,
        boxShadow: isHighlighted
          ? `0 0 20px cyan, 0 0 40px ${colors.glow}`
          : selected
          ? `0 0 20px ${colors.glow}`
          : '0 2px 8px rgba(0,0,0,0.3)',
        ringColor: selected ? `${colors.bg}40` : undefined,
        minWidth: '120px',
        maxWidth: '220px',
      }}
    >
      {/* Color accent bar */}
      <div className="h-1 w-full flex-shrink-0" style={{ backgroundColor: colors.bg }} />

      {/* Content */}
      <div className="px-4 py-3">
        {/* Handles for edge connections */}
        <Handle type="target" position={Position.Top} className="!bg-primary/40" />
        <Handle type="source" position={Position.Bottom} className="!bg-primary/40" />
        <Handle type="target" position={Position.Left} className="!bg-primary/40" />
        <Handle type="source" position={Position.Right} className="!bg-primary/40" />

        <div className="flex items-center gap-1.5 mb-1.5">
          <div
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: colors.bg, boxShadow: `0 0 6px ${colors.glow}` }}
          />
          <span
            className="text-[9px] uppercase tracking-widest font-bold truncate"
            style={{ color: colors.border }}
          >
            {data.nodeType}
          </span>
        </div>
        <p className="text-[13px] font-bold text-white leading-snug break-words whitespace-normal">
          {data.label}
        </p>
        {data.description && (
          <p className="text-[11px] text-text-secondary mt-1.5 leading-snug line-clamp-2 break-words whitespace-normal">
            {data.description}
          </p>
        )}
      </div>
    </div>
  );
}

const nodeTypes = {
  concept: MindmapNode,
  entity: MindmapNode,
  document: MindmapNode,
  fact: MindmapNode,
};

/* ── Inner component (has access to useReactFlow) ── */
function GraphCanvasInner() {
  const { getMindmapForCurrentUser, selectedNode, setSelectedNode, getCurrentUser } = useAppStore();
  const currentUser = getCurrentUser();
  const graphData = getMindmapForCurrentUser();
  const { fitView } = useReactFlow();

  // Hook: citation-click → pan + glow
  useGraphHighlight();

  /* ── Build React Flow nodes/edges from store data ── */
  const initialNodes = useMemo(
    () =>
      graphData.nodes.map((n) => ({
        ...n,
        type: n.type || 'concept',
        selected: n.id === selectedNode,
      })),
    [graphData.nodes, selectedNode],
  );

  const initialEdges = useMemo(
    () =>
      graphData.edges.map((e) => ({
        ...e,
        markerEnd: { type: MarkerType.ArrowClosed, color: e.style?.stroke || '#6366f1' },
        labelStyle: { fill: '#a5b4fc', fontSize: 10, fontWeight: 600 },
        labelBgStyle: { fill: '#111827', fillOpacity: 0.9 },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 6,
      })),
    [graphData.edges],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  /* Sync store → React Flow when user / graph changes */
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  /* ── Resize listener → fitView (spec constraint) ── */
  useEffect(() => {
    let timer;
    const handleResize = () => {
      clearTimeout(timer);
      timer = setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 150);
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timer);
    };
  }, [fitView]);

  /* Node click toggles detail panel */
  const onNodeClick = useCallback(
    (_, node) => setSelectedNode(node.id === selectedNode ? null : node.id),
    [selectedNode, setSelectedNode],
  );

  const selectedNodeData = graphData.nodes.find((n) => n.id === selectedNode);

  return (
    <div className="flex flex-col h-full bg-gradient-subtle">
      {/* ── Mini header / stats bar ── */}
      <header className="flex items-center justify-between px-5 sm:px-6 py-3 border-b border-white/[0.06] bg-surface/80 backdrop-blur-md flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-secondary/30 to-primary/20 flex items-center justify-center ring-1 ring-secondary/20 flex-shrink-0">
            <Network className="w-4 h-4 text-secondary-light" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-text-primary tracking-tight">Mind Map</h2>
            <p className="text-[10px] text-text-secondary mt-0.5 truncate">
              <span className="inline-flex items-center gap-1">
                <CircleDot className="w-3 h-3" />
                {graphData.nodes.length} nodes
              </span>
              <span className="mx-1.5 text-text-muted/30">&bull;</span>
              <span className="inline-flex items-center gap-1">
                <GitBranch className="w-3 h-3" />
                {graphData.edges.length} edges
              </span>
              <span className="mx-1.5 text-text-muted/30">&bull;</span>
              <span className="text-primary-light font-medium">{currentUser.name}</span>
            </p>
          </div>
        </div>
        <Legend />
      </header>

      {/* ── Canvas ── */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          minZoom={0.3}
          maxZoom={2.5}
          panOnDrag
          zoomOnPinch
          zoomOnScroll
          zoomActivationKeyCode="Control"
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1e293b" gap={28} size={1} />
          <Controls position="bottom-left" />
          <MiniMap
            nodeColor={(node) => {
              const m = { concept: '#6366f1', entity: '#8b5cf6', document: '#0ea5e9', fact: '#10b981' };
              return m[node.type] || '#6366f1';
            }}
            maskColor="rgba(3,7,18,0.75)"
            position="bottom-right"
            nodeStrokeWidth={3}
            style={{ height: 120, width: 160 }}
          />
        </ReactFlow>

        {/* Hint overlay */}
        {!selectedNodeData && graphData.nodes.length > 0 && (
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 px-3 py-2 rounded-xl glass text-[11px] text-text-muted/50 animate-fade-in pointer-events-none">
            <MousePointerClick className="w-3.5 h-3.5" />
            Click a node to inspect
          </div>
        )}

        {/* ── Node Detail Panel ── */}
        {selectedNodeData && (
          <div className="absolute top-20 right-4 w-72 sm:w-80 bg-surface backdrop-blur-xl border border-white/[0.08] rounded-2xl shadow-2xl shadow-black/50 overflow-hidden animate-fade-in-scale z-[50] max-h-[calc(100vh-120px)] flex flex-col">
            <div
              className="h-1.5 flex-shrink-0"
              style={{ background: COLOR_MAP[selectedNodeData.data.nodeType]?.bg || '#6366f1' }}
            />
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <Info className="w-4 h-4 text-primary-light" />
                <span className="text-sm font-bold text-text-primary">Node Details</span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="w-7 h-7 rounded-lg hover:bg-white/[0.08] flex items-center justify-center transition-all cursor-pointer"
              >
                <X className="w-4 h-4 text-text-secondary" />
              </button>
            </div>

            <div className="p-5 space-y-5 overflow-y-auto">
              <div className="flex items-center gap-2.5">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: COLOR_MAP[selectedNodeData.data.nodeType]?.bg || '#6366f1', boxShadow: `0 0 8px ${COLOR_MAP[selectedNodeData.data.nodeType]?.glow || 'transparent'}` }}
                />
                <span
                  className="text-xs font-bold uppercase tracking-wider"
                  style={{ color: COLOR_MAP[selectedNodeData.data.nodeType]?.border || '#818cf8' }}
                >
                  {selectedNodeData.data.nodeType}
                </span>
                <span className="text-[10px] font-mono text-text-muted ml-auto">
                  {selectedNodeData.id}
                </span>
              </div>
              <DetailField
                label="Label"
                value={
                  <span className="text-sm font-semibold text-text-primary break-words leading-normal block">
                    {selectedNodeData.data.label}
                  </span>
                }
              />
              <DetailField
                label="Description"
                value={
                  <span className="text-[13px] text-text-secondary leading-relaxed break-words block">
                    {selectedNodeData.data.description || 'No description available'}
                  </span>
                }
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Exported wrapper (ReactFlowProvider lives in App.jsx) ── */
export default function GraphCanvas() {
  return <GraphCanvasInner />;
}

/* ── Helpers ── */
function DetailField({ label, value }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
        {label}
      </span>
      <div className="break-words">
        {value}
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
    <div className="hidden sm:flex items-center gap-0.5 px-2.5 py-1.5 rounded-xl bg-surface-light/30 border border-surface-lighter/30 flex-shrink-0">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-surface-lighter/20 transition-colors"
        >
          <div
            className="w-2 h-2 rounded-full shadow-sm"
            style={{ backgroundColor: item.color, boxShadow: `0 0 6px ${item.color}40` }}
          />
          <span className="text-[10px] text-text-secondary/80 font-medium">{item.label}</span>
        </div>
      ))}
    </div>
  );
}
