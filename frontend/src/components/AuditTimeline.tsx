import type { AuditEntry } from "@/types/triage";
import { formatCost, formatDate, formatDuration, formatModelName } from "@/utils/format";

interface Props {
  entries: AuditEntry[];
}

export function AuditTimeline({ entries }: Props) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted">No audit entries available.</p>;
  }

  return (
    <div className="relative space-y-0">
      {/* Vertical line */}
      <div className="absolute left-3 top-0 h-full w-px bg-border" />

      {entries.map((entry, i) => (
        <div key={i} className="relative flex gap-4 pb-6">
          {/* Dot */}
          <div className="relative z-10 mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-primary ring-4 ring-white" />

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold capitalize">{entry.node}</span>
              <span className="text-xs text-muted">{formatModelName(entry.model_used)}</span>
              <span className="text-xs text-muted">{formatDate(entry.timestamp)}</span>
            </div>
            <div className="mt-1 flex gap-4 text-xs text-muted">
              <span>In: {entry.tokens.in} / Out: {entry.tokens.out}</span>
              <span>{formatDuration(entry.duration_ms)}</span>
              <span>{formatCost(entry.cost_usd)}</span>
            </div>
            {entry.input_summary && (
              <p className="mt-1 text-xs text-muted">
                <span className="font-medium">Input:</span> {entry.input_summary}
              </p>
            )}
            {entry.output_summary && (
              <p className="mt-0.5 text-xs text-muted">
                <span className="font-medium">Output:</span> {entry.output_summary}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
