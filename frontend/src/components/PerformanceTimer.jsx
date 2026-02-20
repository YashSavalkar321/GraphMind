import { Clock } from 'lucide-react';

/**
 * PerformanceTimer — Displays retrieval time in the mandated format:
 * "Retrieval completed in X ms"
 *
 * This metric EXCLUDES LLM response generation time.
 */
export default function PerformanceTimer({ timeMs }) {
  if (timeMs == null) return null;

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-success/10 border border-success/20 mt-1">
      <Clock className="w-3 h-3 text-success" />
      <span className="text-[11px] font-medium text-success">
        Retrieval completed in {timeMs} ms
      </span>
    </div>
  );
}
