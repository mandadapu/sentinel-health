import { useState } from "react";
import type { ApprovalStatus, TriageSession } from "@/types/triage";
import { TriageRow } from "@/components/TriageRow";

interface Props {
  sessions: TriageSession[];
}

const filters: { label: string; value: ApprovalStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
];

export function ApprovalQueue({ sessions }: Props) {
  const [filter, setFilter] = useState<ApprovalStatus | "all">("all");

  const filtered =
    filter === "all" ? sessions : sessions.filter((s) => s.status === filter);

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.value
                ? "bg-primary text-white"
                : "bg-surface-dark text-muted hover:bg-gray-200"
            }`}
          >
            {f.label}
            {f.value !== "all" && (
              <span className="ml-1">
                ({sessions.filter((s) => s.status === f.value).length})
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-white">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border bg-surface">
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Encounter</th>
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Patient</th>
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Level</th>
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Confidence</th>
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Model</th>
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Status</th>
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Flags</th>
              <th className="px-4 py-3 text-xs font-medium uppercase text-muted">Updated</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-muted">
                  No sessions found.
                </td>
              </tr>
            ) : (
              filtered.map((s) => <TriageRow key={s.encounter_id} session={s} />)
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
