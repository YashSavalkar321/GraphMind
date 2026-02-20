import { Bookmark, ChevronRight } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function CitationBadge({ citations }) {
  const { highlightNode, setActiveView } = useAppStore();

  if (!citations || citations.length === 0) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-warning/10 border border-warning/20 w-full">
        <span className="text-sm text-warning/90 font-medium italic">
          No matching memories found — answer not in knowledge base.
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
      <div className="flex items-center gap-2 mb-3">
        <Bookmark className="w-4 h-4 text-primary-light" />
        <span className="text-xs uppercase tracking-widest font-bold text-primary-light/90">
          Memory Citations ({citations.length})
        </span>
      </div>
      
      {/* Safe wrapping container */}
      <div className="flex flex-wrap items-center gap-3">
        {citations.map((cite, i) => (
          <button
            key={`${cite.node_id}-${i}`}
            onClick={() => handleClick(cite)}
            className="group flex flex-row items-center gap-3 px-3.5 py-2.5 rounded-xl bg-primary/20 border border-primary/30 hover:bg-primary/25 hover:border-primary/40 transition-all cursor-pointer shadow-sm max-w-full"
            title={`${cite.snippet} — Click to view on mind map`}
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