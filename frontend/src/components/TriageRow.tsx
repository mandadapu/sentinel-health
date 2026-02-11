import { Link } from "react-router-dom";
import type { TriageSession } from "@/types/triage";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate, formatModelName, triageLevelColor } from "@/utils/format";

export function TriageRow({ session }: { session: TriageSession }) {
  const level = session.triage_decision?.level ?? "—";
  const confidence = session.triage_decision?.confidence;
  const model = session.routing_metadata?.selected_model ?? "";

  return (
    <tr className="border-b border-border hover:bg-surface-dark transition-colors">
      <td className="px-4 py-3 text-sm">
        <Link
          to={`/triage/${session.encounter_id}`}
          className="font-medium text-primary hover:underline"
        >
          {session.encounter_id}
        </Link>
      </td>
      <td className="px-4 py-3 text-sm text-muted">
        {session.patient_id}
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${triageLevelColor(level)}`}>
          {level}
        </span>
      </td>
      <td className="px-4 py-3">
        {confidence != null ? <ConfidenceBadge value={confidence} /> : "—"}
      </td>
      <td className="px-4 py-3 text-sm text-muted">
        {formatModelName(model)}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={session.status} />
      </td>
      <td className="px-4 py-3 text-sm">
        {session.circuit_breaker_tripped && (
          <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            CB Tripped
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-muted">
        {formatDate(session.updated_at)}
      </td>
    </tr>
  );
}
