import { useState } from "react";
import { EncounterForm } from "@/components/EncounterForm";
import { ReasoningChain } from "@/components/ReasoningChain";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { triageLevelColor } from "@/utils/format";
import type { TriageResult } from "@/types/triage";

export function SubmitPage() {
  const [result, setResult] = useState<TriageResult | null>(null);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Submit Encounter</h1>
        <p className="mt-1 text-sm text-muted">
          Enter patient encounter text to run through the triage pipeline.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-white p-6">
        <EncounterForm onResult={setResult} />
      </div>

      {result && (
        <div className="space-y-6">
          <div className="rounded-lg border border-border bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold">Triage Result</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs font-medium text-muted">Level</p>
                <span className={`mt-1 inline-flex rounded border px-2 py-0.5 text-sm font-semibold ${triageLevelColor(result.triage_decision.level)}`}>
                  {result.triage_decision.level}
                </span>
              </div>
              <div>
                <p className="text-xs font-medium text-muted">Confidence</p>
                <div className="mt-1">
                  <ConfidenceBadge value={result.triage_decision.confidence} />
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-muted">Sentinel</p>
                <span className={`mt-1 inline-flex text-sm font-medium ${result.sentinel_check.passed ? "text-green-700" : "text-red-700"}`}>
                  {result.sentinel_check.passed ? "Passed" : "Failed"}
                </span>
              </div>
              <div>
                <p className="text-xs font-medium text-muted">Circuit Breaker</p>
                <span className={`mt-1 inline-flex text-sm font-medium ${result.circuit_breaker_tripped ? "text-red-700" : "text-green-700"}`}>
                  {result.circuit_breaker_tripped ? "Tripped" : "OK"}
                </span>
              </div>
            </div>

            <div className="mt-4">
              <p className="text-xs font-medium text-muted">Reasoning</p>
              <p className="mt-1 text-sm">{result.triage_decision.reasoning_summary}</p>
            </div>

            {result.triage_decision.recommended_actions.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-medium text-muted">Recommended Actions</p>
                <ul className="mt-1 list-inside list-disc text-sm">
                  {result.triage_decision.recommended_actions.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold">Pipeline Trace</h2>
            <ReasoningChain
              routing={result.routing_metadata}
              extraction={result.fhir_data}
              decision={result.triage_decision}
              sentinel={result.sentinel_check}
              auditTrail={result.audit_trail}
            />
          </div>
        </div>
      )}
    </div>
  );
}
