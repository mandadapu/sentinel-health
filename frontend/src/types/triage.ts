export interface Vitals {
  heart_rate: number | null;
  blood_pressure: string | null;
  temperature: number | null;
  respiratory_rate: number | null;
  spo2: number | null;
}

export interface Symptom {
  description: string;
  onset: string;
  severity: string;
}

export interface Medication {
  name: string;
  dose: string;
  frequency: string;
}

export interface PatientHistory {
  conditions: string[];
  allergies: string[];
  surgeries: string[];
}

export interface ExtractedData {
  vitals: Vitals;
  symptoms: Symptom[];
  medications: Medication[];
  history: PatientHistory;
  chief_complaint: string;
  assessment_notes: string;
}

export interface TriageDecision {
  level: "Emergency" | "Urgent" | "Semi-Urgent" | "Non-Urgent";
  confidence: number;
  reasoning_summary: string;
  recommended_actions: string[];
  key_findings: string[];
  model_used?: string;
}

export interface SentinelCheck {
  passed: boolean;
  hallucination_score: number;
  confidence_assessment: number;
  vitals_consistent: boolean;
  medication_safe: boolean;
  issues_found: string[];
  failure_reasons?: string[];
}

export interface RoutingMetadata {
  category: string;
  classifier_confidence: number;
  selected_model: string;
  escalation_reason: string | null;
  safety_override: boolean;
}

export interface AuditEntry {
  node: string;
  timestamp: string;
  model_used: string;
  tokens: { in: number; out: number };
  cost_usd: number;
  duration_ms: number;
  input_summary: string;
  output_summary: string;
}

export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface TriageSession {
  encounter_id: string;
  patient_id: string;
  raw_input: string;
  status: ApprovalStatus;
  triage_level?: TriageDecision["level"];
  circuit_breaker_tripped: boolean;
  routing_metadata?: RoutingMetadata;
  fhir_data?: ExtractedData;
  triage_decision?: TriageDecision;
  sentinel_check?: SentinelCheck;
  audit_trail: AuditEntry[];
  compliance_flags: string[];
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TriageSubmission {
  encounter_text: string;
  patient_id?: string;
}

export interface TriageResult {
  encounter_id: string;
  routing_metadata: RoutingMetadata;
  fhir_data: ExtractedData;
  triage_decision: TriageDecision;
  sentinel_check: SentinelCheck;
  circuit_breaker_tripped: boolean;
  audit_trail: AuditEntry[];
  compliance_flags: string[];
}
