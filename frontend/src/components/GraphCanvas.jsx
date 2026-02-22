import { useCallback, useEffect, useMemo, useState } from 'react';
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
import { Network, Info, X, GitBranch, CircleDot, MousePointerClick, Eye, EyeOff } from 'lucide-react';
import useAppStore from '../store/useAppStore';
import useGraphHighlight from '../hooks/useGraphHighlight';

/* ── Colour palette per node type ── */
const COLOR_MAP = {
  entity:     { bg: '#8b5cf6', border: '#a78bfa', glow: 'rgba(139,92,246,0.35)'  },
  preference: { bg: '#ec4899', border: '#f472b6', glow: 'rgba(236,72,153,0.35)'  },
  goal:       { bg: '#14b8a6', border: '#2dd4bf', glow: 'rgba(20,184,166,0.35)'  },
  event:      { bg: '#f97316', border: '#fb923c', glow: 'rgba(249,115,22,0.35)'  },
  fact:       { bg: '#10b981', border: '#34d399', glow: 'rgba(16,185,129,0.35)'  },
  document:   { bg: '#0ea5e9', border: '#38bdf8', glow: 'rgba(14,165,233,0.35)'  },
  category:   { bg: '#f59e0b', border: '#fcd34d', glow: 'rgba(245,158,11,0.45)'  },
};

/* Legacy + fallback mappings */
const getNodeColor = (nodeType) => COLOR_MAP[nodeType] || COLOR_MAP.entity;

/* ── Custom Node ── */
function MindmapNode({ id, data, selected }) {
  const highlightedNodeId = useAppStore((s) => s.highlightedNodeId);
  const isHighlighted = id === highlightedNodeId;
  const colors = getNodeColor(data.nodeType);

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
  entity: MindmapNode,
  preference: MindmapNode,
  goal: MindmapNode,
  event: MindmapNode,
  fact: MindmapNode,
  document: MindmapNode,
  category: CategoryNode,
};

/* ── Category Hub Node ── */
function CategoryNode({ id, data, selected }) {
  const highlightedNodeId = useAppStore((s) => s.highlightedNodeId);
  const isHighlighted = id === highlightedNodeId;
  const colors = COLOR_MAP.category;
  return (
    <div
      className={`relative flex items-center justify-center rounded-2xl border-2 shadow-xl transition-all duration-300 ${
        selected || isHighlighted ? 'scale-110 shadow-2xl ring-2' : 'hover:scale-105'
      }`}
      style={{
        backgroundColor: '#1c1a14',
        borderColor: colors.border,
        boxShadow: `0 0 18px ${colors.glow}, 0 4px 12px rgba(0,0,0,0.4)`,
        minWidth: '110px',
        padding: '10px 18px',
      }}
    >
      <Handle type="target" position={Position.Top}    className="!bg-amber-400/40" />
      <Handle type="source" position={Position.Bottom} className="!bg-amber-400/40" />
      <Handle type="target" position={Position.Left}   className="!bg-amber-400/40" />
      <Handle type="source" position={Position.Right}  className="!bg-amber-400/40" />
      <div className="flex flex-col items-center gap-1">
        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colors.bg, boxShadow: `0 0 8px ${colors.glow}` }} />
        <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: colors.border }}>
          {data.label}
        </span>
        {data.description && (
          <span className="text-[10px] text-text-muted">{data.description}</span>
        )}
      </div>
    </div>
  );
}

/* ── Filter Toggle Buttons ── */
const FILTER_GROUPS = [
  // Always visible by default
  { key: 'entity',     label: 'Entity',     defaultOn: true },
  { key: 'preference', label: 'Preference', defaultOn: true },
  { key: 'goal',       label: 'Goal',       defaultOn: true },
  { key: 'event',      label: 'Event',      defaultOn: true },
  // Hidden by default (toggleable)
  { key: 'fact',       label: 'Fact',        defaultOn: false },
  { key: 'document',   label: 'Document',    defaultOn: false },
];

function FilterToggles({ visibleTypes, onToggle }) {
  return (
    <div className="hidden sm:flex items-center gap-0.5 px-2.5 py-1.5 rounded-xl bg-surface-light/30 border border-surface-lighter/30 flex-shrink-0">
      {FILTER_GROUPS.map((item) => {
        const isOn = visibleTypes.has(item.key);
        const colors = getNodeColor(item.key);
        return (
          <button
            key={item.key}
            onClick={() => onToggle(item.key)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-all duration-200 cursor-pointer ${
              isOn
                ? 'bg-surface-lighter/30 shadow-sm'
                : 'opacity-40 hover:opacity-70'
            }`}
            title={`${isOn ? 'Hide' : 'Show'} ${item.label} nodes`}
          >
            <div
              className="w-2 h-2 rounded-full shadow-sm transition-all"
              style={{
                backgroundColor: isOn ? colors.bg : '#4b5563',
                boxShadow: isOn ? `0 0 6px ${colors.bg}40` : 'none',
              }}
            />
            <span className={`text-[10px] font-medium transition-colors ${
              isOn ? 'text-text-secondary/90' : 'text-text-muted/50'
            }`}>
              {item.label}
            </span>
            {isOn ? (
              <Eye className="w-2.5 h-2.5 text-text-muted/60" />
            ) : (
              <EyeOff className="w-2.5 h-2.5 text-text-muted/30" />
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ── Inner component (has access to useReactFlow) ── */
function GraphCanvasInner() {
  const graphData = useAppStore((s) => s.getMindmapForCurrentUser());
  const currentUser = useAppStore((s) => s.getCurrentUser());
  const selectedNode = useAppStore((s) => s.selectedNode);
  const setSelectedNode = useAppStore((s) => s.setSelectedNode);
  const { fitView } = useReactFlow();

  // Focus mode: which node ID is currently focused (neighbourhood shown)
  const [focusedNodeId, setFocusedNodeId] = useState(null);

  // Type visibility filter
  const [visibleTypes, setVisibleTypes] = useState(() => {
    const initial = new Set();
    FILTER_GROUPS.forEach((g) => { if (g.defaultOn) initial.add(g.key); });
    return initial;
  });

  const handleToggleType = useCallback((typeKey) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (next.has(typeKey)) {
        next.delete(typeKey);
      } else {
        next.add(typeKey);
      }
      return next;
    });
  }, []);

  // Store-level retrieval focus (set from CitationBadge "Show subgraph" button)
  const retrievalFocusNodeIds = useAppStore((s) => s.retrievalFocusNodeIds);
  const clearRetrievalFocus   = useAppStore((s) => s.clearRetrievalFocus);

  // Hook: citation-click → pan + glow
  useGraphHighlight();

  /* ── Build React Flow nodes/edges from store data ── */
  const initialNodes = useMemo(
    () =>
      (graphData?.nodes || []).map((n) => ({
        ...n,
        type: n.type || 'entity',
        selected: n.id === selectedNode,
      })),
    [graphData?.nodes],
  );

  const initialEdges = useMemo(
    () =>
      (graphData?.edges || []).map((e) => ({
        ...e,
        markerEnd: { type: MarkerType.ArrowClosed, color: e.style?.stroke || '#6366f1' },
        labelStyle: { fill: '#a5b4fc', fontSize: 10, fontWeight: 600 },
        labelBgStyle: { fill: '#111827', fillOpacity: 0.9 },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 6,
      })),
    [graphData?.edges],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  /* Sync store → React Flow when user / graph changes */
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  /* Sync selected state without resetting positions */
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        selected: n.id === selectedNode,
      }))
    );
  }, [selectedNode, setNodes]);

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

  /* ── Focus-mode: compute 1-hop neighbourhood ──
     Priority: retrievalFocusNodeIds (from citations) > local focusedNodeId */
  const neighborIds = useMemo(() => {
    const focalSet = retrievalFocusNodeIds ?? (focusedNodeId ? new Set([focusedNodeId]) : null);
    if (!focalSet) return null;
    const ids = new Set(focalSet);
    (graphData?.edges || []).forEach((e) => {
      if (focalSet.has(e.source)) ids.add(e.target);
      if (focalSet.has(e.target)) ids.add(e.source);
    });
    return ids;
  }, [focusedNodeId, retrievalFocusNodeIds, graphData?.edges]);

  const isRetrievalMode = !!retrievalFocusNodeIds;

  /* ── Type-based + focus-mode filtering ── */
  const displayNodes = useMemo(
    () =>
      nodes
        .filter((n) => {
          const nodeType = n.data?.nodeType || n.type || 'entity';
          // Category nodes are always visible
          if (nodeType === 'category') return true;
          // If node is in focus/neighbour set, always show (click-to-expand)
          if (neighborIds?.has(n.id)) return true;
          // Otherwise, check the type visibility filter
          return visibleTypes.has(nodeType);
        })
        .map((n) => ({
          ...n,
          style: {
            ...n.style,
            opacity: neighborIds ? (neighborIds.has(n.id) ? 1 : 0.07) : 1,
            transition: 'opacity 0.25s ease',
            pointerEvents: neighborIds && !neighborIds.has(n.id) ? 'none' : 'auto',
          },
        })),
    [nodes, neighborIds, visibleTypes],
  );

  // Build set of visible node IDs for edge filtering
  const visibleNodeIds = useMemo(
    () => new Set(displayNodes.map((n) => n.id)),
    [displayNodes],
  );

  const displayEdges = useMemo(
    () =>
      edges
        .filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
        .map((e) => {
          const visible = !neighborIds ||
            (neighborIds.has(e.source) && neighborIds.has(e.target));
          return {
            ...e,
            style: { ...e.style, opacity: visible ? 1 : 0.04, transition: 'opacity 0.25s ease' },
            animated: visible && !!focusedNodeId,
          };
        }),
    [edges, neighborIds, focusedNodeId, visibleNodeIds],
  );

  /* Node click: toggle focus + detail panel */
  const onNodeClick = useCallback(
    (_, node) => {
      const isSame = node.id === focusedNodeId;
      setFocusedNodeId(isSame ? null : node.id);
      setSelectedNode(isSame ? null : node.id);
    },
    [focusedNodeId, setSelectedNode],
  );

  /* Pane click: clear all focus modes */
  const onPaneClick = useCallback(() => {
    setFocusedNodeId(null);
    setSelectedNode(null);
    clearRetrievalFocus();
  }, [setSelectedNode, clearRetrievalFocus]);

  const selectedNodeData = (graphData?.nodes || []).find((n) => n.id === selectedNode);

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
                {graphData?.nodes?.length || 0} nodes
              </span>
              <span className="mx-1.5 text-text-muted/30">&bull;</span>
              <span className="inline-flex items-center gap-1">
                <GitBranch className="w-3 h-3" />
                {graphData?.edges?.length || 0} edges
              </span>
              <span className="mx-1.5 text-text-muted/30">&bull;</span>
              <span className="text-primary-light font-medium">{currentUser?.name || 'Guest'}</span>
            </p>
          </div>
        </div>
        <FilterToggles visibleTypes={visibleTypes} onToggle={handleToggleType} />
      </header>

      {/* ── Canvas ── */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={displayNodes}
          edges={displayEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
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
              const colors = getNodeColor(node.type);
              return colors.bg;
            }}
            maskColor="rgba(3,7,18,0.75)"
            position="bottom-right"
            nodeStrokeWidth={3}
            style={{ height: 120, width: 160 }}
          />
        </ReactFlow>

        {/* Retrieval subgraph banner */}
        {isRetrievalMode && neighborIds && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2.5 px-4 py-2 rounded-xl bg-surface border border-success/40 shadow-lg shadow-black/40 text-[11px] animate-fade-in">
            <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
            <span className="text-text-primary font-medium">
              Retrieval subgraph &mdash; <span className="text-success font-bold">{retrievalFocusNodeIds.size}</span> source node{retrievalFocusNodeIds.size !== 1 ? 's' : ''} +{' '}
              <span className="text-success font-bold">{neighborIds.size - retrievalFocusNodeIds.size}</span> neighbour{neighborIds.size - retrievalFocusNodeIds.size !== 1 ? 's' : ''}
            </span>
            <span className="text-text-muted/40">·</span>
            <span className="text-text-muted text-[10px]">click canvas to reset</span>
            <button
              onClick={onPaneClick}
              className="w-5 h-5 rounded-md hover:bg-white/10 flex items-center justify-center transition-colors cursor-pointer ml-1"
            >
              <X className="w-3 h-3 text-text-muted" />
            </button>
          </div>
        )}

        {/* Manual focus banner */}
        {!isRetrievalMode && focusedNodeId && neighborIds && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2.5 px-4 py-2 rounded-xl bg-surface border border-primary/30 shadow-lg shadow-black/40 text-[11px] animate-fade-in">
            <div className="w-2 h-2 rounded-full bg-primary-light animate-pulse" />
            <span className="text-text-primary font-medium">
              Showing <span className="text-primary-light font-bold">{neighborIds.size}</span> connected node{neighborIds.size !== 1 ? 's' : ''}
            </span>
            <span className="text-text-muted/40">·</span>
            <span className="text-text-muted text-[10px]">click canvas to reset</span>
            <button
              onClick={onPaneClick}
              className="w-5 h-5 rounded-md hover:bg-white/10 flex items-center justify-center transition-colors cursor-pointer ml-1"
            >
              <X className="w-3 h-3 text-text-muted" />
            </button>
          </div>
        )}

        {/* Hint overlay */}
        {!focusedNodeId && !selectedNodeData && (graphData?.nodes?.length || 0) > 0 && (
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 px-3 py-2 rounded-xl glass text-[11px] text-text-muted/50 animate-fade-in pointer-events-none">
            <MousePointerClick className="w-3.5 h-3.5" />
            Click a node to focus its neighbourhood
          </div>
        )}

        {/* ── Node Detail Panel ── */}
        {selectedNodeData && (
          <div className="absolute top-20 right-4 w-72 sm:w-80 bg-surface backdrop-blur-xl border border-white/[0.08] rounded-2xl shadow-2xl shadow-black/50 overflow-hidden animate-fade-in-scale z-[50] max-h-[calc(100vh-120px)] flex flex-col">
            <div
              className="h-1.5 flex-shrink-0"
              style={{ background: getNodeColor(selectedNodeData.data.nodeType)?.bg || '#8b5cf6' }}
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
                  style={{ backgroundColor: getNodeColor(selectedNodeData.data.nodeType)?.bg || '#8b5cf6', boxShadow: `0 0 8px ${getNodeColor(selectedNodeData.data.nodeType)?.glow || 'transparent'}` }}
                />
                <span
                  className="text-xs font-bold uppercase tracking-wider"
                  style={{ color: getNodeColor(selectedNodeData.data.nodeType)?.border || '#a78bfa' }}
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

