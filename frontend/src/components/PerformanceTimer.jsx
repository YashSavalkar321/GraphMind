import { Clock, Zap } from 'lucide-react';

/**
 * PerformanceTimer — Mandatory "Retrieval completed in X ms" badge.
 *
 * "This is a pass/fail requirement for the hackathon."
 * Must never be truncated or hidden by horizontal scrolling.
 */
export default function PerformanceTimer({ timeMs }) {
  if (timeMs == null) return null;

  const isFast = timeMs < 50;

  return (
    <div
      className={`inline-flex w-fit items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-semibold transition-all ${
        isFast
          ? 'bg-success/10 border-success/25 text-success shadow-[0_0_12px_rgba(52,211,153,0.12)]'
          : 'bg-warning/10 border-warning/25 text-warning shadow-[0_0_12px_rgba(251,191,36,0.12)]'
      }`}
    >
      {isFast ? (
        <Zap className="w-3 h-3 flex-shrink-0" />
      ) : (
        <Clock className="w-3 h-3 flex-shrink-0" />
      )}
      <span className="whitespace-nowrap">
        Retrieval completed in <span className="font-mono font-bold">{timeMs} ms</span>
      </span>
    </div>
  );
}
