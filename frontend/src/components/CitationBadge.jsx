import { Bookmark, ChevronRight, Network } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function CitationBadge({ citations, broadQuery = false }) {
  const highlightNode = useAppStore((s) => s.highlightNode);
  const setActiveView = useAppStore((s) => s.setActiveView);
  const focusRetrievalNodes = useAppStore((s) => s.focusRetrievalNodes);

  const isHistoryAnswer =
    !citations || citations.length === 0
      ? false
      : citations.every((c) => c.title === 'Conversation History');

  if (!citations || citations.length === 0) {
    if (broadQuery) {
      return (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-secondary/10 border border-secondary/20 w-full">
          <span className="text-sm text-secondary-light/90 font-medium italic">
            Answered from conversation context.
          </span>
        </div>
      );
    }
    return null;
  }

  if (isHistoryAnswer) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-secondary/10 border border-secondary/20 w-full">
        <span className="text-sm text-secondary-light/90 font-medium italic">
          Answered from conversation history ({citations.length} exchange{citations.length !== 1 ? 's' : ''} referenced).
        </span>
      </div>
    );
  }

  const handleClick = (citation) => {
    highlightNode(citation.node_id);
    setActiveView('graph');
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Bookmark className="w-4 h-4 text-primary-light" />
          <span className="text-xs uppercase tracking-widest font-bold text-primary-light/90">
            Memory Citations ({citations.length})
          </span>
        </div>
        <button
          onClick={() => focusRetrievalNodes(citations.map((c) => c.node_id))}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/15 border border-success/30 hover:bg-success/25 hover:border-success/50 transition-all cursor-pointer text-[11px] font-semibold text-success"
          title="Show all cited nodes and their neighbours in the mind map"
        >
          <Network className="w-3.5 h-3.5" />
          Show subgraph
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {citations.map((cite, i) => (
          <button
            key={`${cite.node_id}-${i}`}
            onClick={() => handleClick(cite)}
            className="group flex flex-row items-center gap-3 px-3.5 py-2.5 rounded-xl bg-primary/20 border border-primary/30 hover:bg-primary/25 hover:border-primary/40 transition-all cursor-pointer shadow-sm max-w-full"
            title={`${cite.snippet} - Click to view on mind map`}
          >
            <span className="text-xs font-mono font-semibold text-primary-light group-hover:text-white bg-primary/15 px-2 py-1 rounded transition-colors flex-shrink-0">
              {cite.node_id}
            </span>
            <span className="text-sm text-text-primary font-medium group-hover:text-white transition-colors truncate">
              {cite.title}
            </span>
            <ChevronRight className="w-4 h-4 text-primary-light/40 group-hover:text-primary-light group-hover:translate-x-1 transition-transform flex-shrink-0 ml-auto" />
          </button>
        ))}
      </div>
    </div>
  );
}
