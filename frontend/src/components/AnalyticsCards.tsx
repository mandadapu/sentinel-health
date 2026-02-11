import type { TriageSession } from "@/types/triage";
import { formatModelName } from "@/utils/format";

interface Props {
  sessions: TriageSession[];
}

export function AnalyticsCards({ sessions }: Props) {
  const total = sessions.length;
  const pending = sessions.filter((s) => s.status === "pending").length;
  const cbTripped = sessions.filter((s) => s.circuit_breaker_tripped).length;

  // Model distribution
  const modelCounts: Record<string, number> = {};
  for (const s of sessions) {
    const model = s.routing_metadata?.selected_model;
    if (model) {
      const name = formatModelName(model);
      modelCounts[name] = (modelCounts[name] ?? 0) + 1;
    }
  }
  const topModel =
    Object.entries(modelCounts).sort(([, a], [, b]) => b - a)[0] ?? null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card label="Total Encounters" value={total} />
      <Card label="Pending Review" value={pending} accent={pending > 0 ? "yellow" : undefined} />
      <Card label="Circuit Breakers" value={cbTripped} accent={cbTripped > 0 ? "red" : undefined} />
      <Card
        label="Top Model"
        value={topModel ? `${topModel[0]} (${topModel[1]})` : "—"}
      />
    </div>
  );
}

function Card({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: "yellow" | "red";
}) {
  const accentClass =
    accent === "red"
      ? "border-l-red-500"
      : accent === "yellow"
        ? "border-l-yellow-500"
        : "border-l-primary";

  return (
    <div className={`rounded-lg border border-border bg-white p-5 border-l-4 ${accentClass}`}>
      <p className="text-sm font-medium text-muted">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
