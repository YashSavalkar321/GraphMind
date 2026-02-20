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
      className={`inline-flex flex-wrap items-center gap-2 px-3 md:px-4 py-1.5 md:py-2 rounded-full border transition-all ${
        isFast ? 'bg-success/8 border-success/20' : 'bg-warning/8 border-warning/20'
      }`}
    >
      <div
        className={`flex items-center justify-center w-5 h-5 rounded-full flex-shrink-0 ${
          isFast ? 'bg-success/20' : 'bg-warning/20'
        }`}
      >
        {isFast ? (
          <Zap className="w-2.5 h-2.5 text-success" />
        ) : (
          <Clock className="w-2.5 h-2.5 text-warning" />
        )}
      </div>
      <span
        className={`text-xs md:text-sm font-semibold whitespace-nowrap ${
          isFast ? 'text-success' : 'text-warning'
        }`}
      >
        Retrieval completed in {timeMs} ms
      </span>
    </div>
  );
}
