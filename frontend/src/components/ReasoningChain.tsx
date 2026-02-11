import type { ExtractedData, RoutingMetadata, SentinelCheck, TriageDecision, AuditEntry } from "@/types/triage";
import { formatConfidence, formatCost, formatDuration, formatModelName } from "@/utils/format";

interface Props {
  routing: RoutingMetadata;
  extraction: ExtractedData;
  decision: TriageDecision;
  sentinel: SentinelCheck;
  auditTrail: AuditEntry[];
}

export function ReasoningChain({ routing, extraction, decision, sentinel, auditTrail }: Props) {
  return (
    <div className="space-y-4">
      {/* Routing */}
      <StepCard
        title="1. Classify & Route"
        model={formatModelName("claude-haiku-4-5-20241022")}
        audit={auditTrail.find((a) => a.node === "classifier")}
      >
        <KV label="Category" value={routing.category} />
        <KV label="Confidence" value={formatConfidence(routing.classifier_confidence)} />
        <KV label="Routed to" value={formatModelName(routing.selected_model)} />
        {routing.safety_override && (
          <span className="mt-1 inline-block rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            Safety Override
          </span>
        )}
      </StepCard>

      {/* Extraction */}
      <StepCard
        title="2. Extractor"
        model={formatModelName(routing.selected_model)}
        audit={auditTrail.find((a) => a.node === "extractor")}
      >
        <KV label="Chief Complaint" value={extraction.chief_complaint} />
        <KV label="Symptoms" value={extraction.symptoms.map((s) => s.description).join(", ")} />
        <KV label="Medications" value={extraction.medications.map((m) => `${m.name} ${m.dose}`).join(", ") || "None"} />
      </StepCard>

      {/* Reasoner */}
      <StepCard
        title="3. Reasoner"
        model={formatModelName(routing.selected_model)}
        audit={auditTrail.find((a) => a.node === "reasoner")}
      >
        <KV label="Level" value={decision.level} />
        <KV label="Confidence" value={formatConfidence(decision.confidence)} />
        <KV label="Key Findings" value={decision.key_findings.join(", ")} />
      </StepCard>

      {/* Sentinel */}
      <StepCard
        title="4. Sentinel"
        model="Haiku"
        audit={auditTrail.find((a) => a.node === "sentinel")}
      >
        <KV label="Passed" value={sentinel.passed ? "Yes" : "No"} />
        <KV label="Hallucination" value={formatConfidence(sentinel.hallucination_score)} />
        <KV label="Vitals Consistent" value={sentinel.vitals_consistent ? "Yes" : "No"} />
        <KV label="Medication Safe" value={sentinel.medication_safe ? "Yes" : "No"} />
        {sentinel.issues_found.length > 0 && (
          <div className="mt-1">
            <span className="text-xs font-medium text-muted">Issues: </span>
            <span className="text-xs text-red-600">{sentinel.issues_found.join("; ")}</span>
          </div>
        )}
      </StepCard>
    </div>
  );
}

function StepCard({
  title,
  model,
  audit,
  children,
}: {
  title: string;
  model: string;
  audit?: AuditEntry;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <div className="flex items-center gap-3 text-xs text-muted">
          <span>{model}</span>
          {audit && (
            <>
              <span>{formatDuration(audit.duration_ms)}</span>
              <span>{formatCost(audit.cost_usd)}</span>
            </>
          )}
        </div>
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="font-medium text-muted">{label}:</span>
      <span>{value}</span>
    </div>
  );
}
