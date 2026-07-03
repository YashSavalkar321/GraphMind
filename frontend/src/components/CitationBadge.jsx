import { Bookmark, ChevronRight, Network, History } from 'lucide-react';
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
        <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-secondary/10 border border-secondary/25 w-full">
          <History className="w-3.5 h-3.5 text-secondary-light/80 flex-shrink-0" />
          <span className="text-xs text-secondary-light/90 font-medium italic">
            Answered from conversation context.
          </span>
        </div>
      );
    }
    return null;
  }

  if (isHistoryAnswer) {
    return (
      <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-secondary/10 border border-secondary/25 w-full">
        <History className="w-3.5 h-3.5 text-secondary-light/80 flex-shrink-0" />
        <span className="text-xs text-secondary-light/90 font-medium italic">
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
      <div className="flex items-center justify-between gap-2 mb-2.5 flex-wrap">
        <div className="flex items-center gap-2">
          <Bookmark className="w-3.5 h-3.5 text-accent-light" />
          <span className="text-[10px] uppercase tracking-[0.22em] font-bold text-accent-light/90">
            Grounded in memory ({citations.length})
          </span>
        </div>
        <button
          onClick={() => focusRetrievalNodes(citations.map((c) => c.node_id))}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/12 border border-success/30 hover:bg-success/20 hover:border-success/50 hover:shadow-[0_0_16px_rgba(52,211,153,0.25)] transition-all cursor-pointer text-[11px] font-semibold text-success"
          title="Show all cited nodes and their neighbours in the mind map"
        >
          <Network className="w-3.5 h-3.5" />
          Show subgraph
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {citations.map((cite, i) => (
          <button
            key={`${cite.node_id}-${i}`}
            onClick={() => handleClick(cite)}
            className="group flex flex-row items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-xl bg-primary/12 border border-primary/30 hover:bg-primary/20 hover:border-primary/50 hover:shadow-[0_0_18px_rgba(99,102,241,0.3)] transition-all cursor-pointer max-w-full"
            title={`${cite.snippet || cite.title} — click to view on mind map`}
          >
            <span className="text-[10px] font-mono font-semibold text-primary-light bg-primary/15 border border-primary/20 px-1.5 py-0.5 rounded-md flex-shrink-0 group-hover:text-white transition-colors">
              {cite.node_id}
            </span>
            <span className="text-xs text-text-primary font-medium group-hover:text-white transition-colors truncate">
              {cite.title}
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-primary-light/40 group-hover:text-primary-light group-hover:translate-x-0.5 transition-all flex-shrink-0" />
          </button>
        ))}
      </div>
    </div>
  );
}
