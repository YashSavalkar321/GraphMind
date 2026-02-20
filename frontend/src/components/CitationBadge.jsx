import { Bookmark, ExternalLink } from 'lucide-react';
import useAppStore from '../store/useAppStore';

/**
 * CitationBadge — Renders memory_citations as clickable badges.
 * Clicking a citation highlights the corresponding node on the mindmap.
 */
export default function CitationBadge({ citations }) {
  const { setSelectedNode, setActiveView } = useAppStore();

  if (!citations || citations.length === 0) return null;

  const handleCitationClick = (citation) => {
    setSelectedNode(citation.node_id);
    setActiveView('graph');
  };

  return (
    <div className="mt-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Bookmark className="w-3 h-3 text-accent" />
        <span className="text-[10px] uppercase tracking-wider font-semibold text-accent">
          Memory Citations
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((cite, i) => (
          <button
            key={`${cite.node_id}-${i}`}
            onClick={() => handleCitationClick(cite)}
            className="group inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-accent/10 border border-accent/20 hover:bg-accent/20 hover:border-accent/40 transition-all cursor-pointer"
            title={cite.snippet}
          >
            <span className="text-[10px] font-mono text-accent/70 group-hover:text-accent">{cite.node_id}</span>
            <span className="text-[11px] text-text-primary font-medium">{cite.title}</span>
            <ExternalLink className="w-2.5 h-2.5 text-accent/50 group-hover:text-accent" />
          </button>
        ))}
      </div>
    </div>
  );
}
