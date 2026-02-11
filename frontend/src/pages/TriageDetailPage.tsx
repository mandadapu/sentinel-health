import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTriageSessions } from "@/hooks/useTriageSessions";
import { useAuditTrail } from "@/hooks/useAuditTrail";
import { useAuthContext } from "@/context/AuthContext";
import { ReasoningChain } from "@/components/ReasoningChain";
import { AuditTimeline } from "@/components/AuditTimeline";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { toast } from "@/components/Toast";
import { triageLevelColor } from "@/utils/format";

export function TriageDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthContext();
  const { sessions, updateApproval } = useTriageSessions();
  const { entries: auditEntries, loading: auditLoading } = useAuditTrail(id);
  const [notes, setNotes] = useState("");

  const session = sessions.find((s) => s.encounter_id === id);

  if (!session) {
    return (
      <div className="py-20 text-center">
        <p className="text-muted">Session not found or loading...</p>
        <Link to="/" className="mt-2 inline-block text-sm text-primary hover:underline">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  async function handleApproval(status: "approved" | "rejected") {
    if (!id || !user?.email) return;
    try {
      await updateApproval(id, status, user.email, notes);
      toast(`Encounter ${status}`, "success");
      setNotes("");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Update failed", "error");
    }
  }

  const decision = session.triage_decision;
  const sentinel = session.sentinel_check;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/" className="text-sm text-muted hover:underline">
            &larr; Dashboard
          </Link>
          <h1 className="mt-1 text-2xl font-bold">{session.encounter_id}</h1>
          <p className="text-sm text-muted">Patient: {session.patient_id}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={session.status} />
          {session.status === "pending" && (
            <div className="space-y-2">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Reviewer notes (optional)"
                className="w-64 rounded-md border border-border px-3 py-2 text-sm"
                rows={2}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => void handleApproval("approved")}
                  className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                >
                  Approve
                </button>
                <button
                  onClick={() => void handleApproval("rejected")}
                  className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
                >
                  Reject
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Summary cards */}
      {decision && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-border bg-white p-4">
            <p className="text-xs font-medium text-muted">Triage Level</p>
            <span className={`mt-1 inline-flex rounded border px-2 py-0.5 text-sm font-semibold ${triageLevelColor(decision.level)}`}>
              {decision.level}
            </span>
          </div>
          <div className="rounded-lg border border-border bg-white p-4">
            <p className="text-xs font-medium text-muted">Confidence</p>
            <div className="mt-1">
              <ConfidenceBadge value={decision.confidence} />
            </div>
          </div>
          <div className="rounded-lg border border-border bg-white p-4">
            <p className="text-xs font-medium text-muted">Sentinel</p>
            <span className={`mt-1 inline-flex text-sm font-medium ${sentinel?.passed ? "text-green-700" : "text-red-700"}`}>
              {sentinel?.passed ? "Passed" : "Failed"}
            </span>
          </div>
          <div className="rounded-lg border border-border bg-white p-4">
            <p className="text-xs font-medium text-muted">Circuit Breaker</p>
            <span className={`mt-1 inline-flex text-sm font-medium ${session.circuit_breaker_tripped ? "text-red-700" : "text-green-700"}`}>
              {session.circuit_breaker_tripped ? "Tripped" : "OK"}
            </span>
          </div>
        </div>
      )}

      {/* Raw input */}
      <div className="rounded-lg border border-border bg-white p-6">
        <h2 className="mb-2 text-lg font-semibold">Encounter Input</h2>
        <p className="whitespace-pre-wrap text-sm">{session.raw_input}</p>
      </div>

      {/* Reasoning chain */}
      {session.routing_metadata && session.fhir_data && decision && sentinel && (
        <div className="rounded-lg border border-border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold">Reasoning Chain</h2>
          <ReasoningChain
            routing={session.routing_metadata}
            extraction={session.fhir_data}
            decision={decision}
            sentinel={sentinel}
            auditTrail={session.audit_trail}
          />
        </div>
      )}

      {/* Audit timeline */}
      <div className="rounded-lg border border-border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold">Audit Trail</h2>
        {auditLoading ? (
          <div className="flex justify-center py-4">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : (
          <AuditTimeline entries={auditEntries.length > 0 ? auditEntries : session.audit_trail} />
        )}
      </div>

      {/* Compliance flags */}
      {session.compliance_flags.length > 0 && (
        <div className="rounded-lg border border-border bg-white p-6">
          <h2 className="mb-2 text-lg font-semibold">Compliance Flags</h2>
          <div className="flex flex-wrap gap-2">
            {session.compliance_flags.map((flag) => (
              <span
                key={flag}
                className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700"
              >
                {flag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
