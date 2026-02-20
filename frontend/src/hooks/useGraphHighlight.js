import { useEffect } from 'react';
import { useReactFlow } from '@xyflow/react';
import useAppStore from '../store/useAppStore';

/**
 * useGraphHighlight — Custom hook satisfying the "Auditability" rule.
 *
 * When a citation badge is clicked in ChatWindow the store's
 * `highlightedNodeId` is set.  This hook reacts by
 *   1. Panning + zooming React Flow to centre the highlighted node.
 *   2. Returning the id so MindmapNode can apply a cyan glow style.
 *
 * Must be called inside a component wrapped by <ReactFlowProvider>.
 */
export default function useGraphHighlight() {
  const { fitView } = useReactFlow();
  const highlightedNodeId = useAppStore((s) => s.highlightedNodeId);

  useEffect(() => {
    if (!highlightedNodeId) return;

    // Small delay lets React Flow finish any pending updates first
    const timer = setTimeout(() => {
      fitView({
        nodes: [{ id: highlightedNodeId }],
        duration: 800,
        padding: 0.3,
      });
    }, 120);

    return () => clearTimeout(timer);
  }, [highlightedNodeId, fitView]);

  return highlightedNodeId;
}
