import { Bookmark, ChevronRight } from 'lucide-react';
import useAppStore from '../store/useAppStore';

/**
 * CitationBadge — Renders memory_citations as clickable badges.
 *
 * Clicking a citation:
 *   1. Highlights the node on the mindmap (cyan glow + fitView).
 *   2. On mobile, auto-switches to the Mindmap tab.
 *
 * If no citations exist, shows a "no memory" fallback.
 */
export default function CitationBadge({ citations }) {
  const { highlightNode, setActiveView } = useAppStore();

  if (!citations || citations.length === 0) {
    return (
      <div className="flex items-center gap-2.5 px-3 md:px-4 py-2.5 rounded-xl bg-warning/6 border border-warning/15 mt-1 flex-wrap">
        <span className="text-[11px] text-warning/80 font-medium italic leading-relaxed">
          No matching memories found — answer not in knowledge base
        </span>
      </div>
    );
  }

  const handleClick = (citation) => {
    // 1. Highlight + pan on graph
    highlightNode(citation.node_id);
    // 2. On mobile, switch to mindmap tab automatically
    setActiveView('graph');
  };

  return (
    <div className="mt-1">
      <div className="flex items-center gap-1.5 mb-2">
        <Bookmark className="w-3 h-3 text-accent flex-shrink-0" />
        <span className="text-[10px] uppercase tracking-widest font-bold text-accent/80">
          Memory Citations ({citations.length})
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {citations.map((cite, i) => (
          <button
            key={`${cite.node_id}-${i}`}
            onClick={() => handleClick(cite)}
            className="group inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-accent/6 border border-accent/15 hover:bg-accent/15 hover:border-accent/35 hover:shadow-sm hover:shadow-accent/10 transition-all duration-200 cursor-pointer btn-press overflow-hidden"
            title={`${cite.snippet} — Click to view on mind map`}
          >
            <span className="text-[10px] font-mono text-accent/50 group-hover:text-accent bg-accent/10 px-1.5 py-0.5 rounded-md transition-colors flex-shrink-0">
              {cite.node_id}
            </span>
            <span className="text-[11px] text-text-primary font-medium group-hover:text-white transition-colors truncate max-w-[140px]">
              {cite.title}
            </span>
            <ChevronRight className="w-3 h-3 text-accent/30 group-hover:text-accent group-hover:translate-x-0.5 transition-all flex-shrink-0" />
          </button>
        ))}
      </div>
    </div>
  );
}
