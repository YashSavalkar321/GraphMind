import { Clock, Zap } from 'lucide-react';

/**
 * PerformanceTimer — Mandatory "Retrieval completed in X ms" badge.
 *
 * "This is a pass/fail requirement for the hackathon."
 * Must never be truncated or hidden by horizontal scrolling.
 * Uses flex-wrap + text-xs md:text-sm for responsive scaling.
 */
export default function PerformanceTimer({ timeMs }) {
  if (timeMs == null) return null;

  const isFast = timeMs < 50;

  return (
    <div
      className={`inline-flex w-fit items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold transition-all ${
        isFast ? 'bg-success/10 border-success/20 text-success' : 'bg-warning/10 border-warning/20 text-warning'
      }`}
    >
      {isFast ? (
        <Zap className="w-3 h-3 flex-shrink-0" />
      ) : (
        <Clock className="w-3 h-3 flex-shrink-0" />
      )}
      <span className="whitespace-nowrap">
        Retrieval completed in {timeMs} ms
      </span>
    </div>
  );
}
