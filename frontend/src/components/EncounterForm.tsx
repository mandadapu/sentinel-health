import { useState, type FormEvent } from "react";
import { apiPost } from "@/services/api";
import { toast } from "@/components/Toast";
import type { TriageResult, TriageSubmission } from "@/types/triage";
import { doc, setDoc } from "firebase/firestore";
import { db } from "@/services/firebase";
import { useAuthContext } from "@/context/AuthContext";

interface Props {
  onResult: (result: TriageResult) => void;
}

export function EncounterForm({ onResult }: Props) {
  const { user } = useAuthContext();
  const [text, setText] = useState("");
  const [patientId, setPatientId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (text.trim().length < 10) {
      toast("Encounter text must be at least 10 characters", "error");
      return;
    }

    setSubmitting(true);
    try {
      const body: TriageSubmission = {
        encounter_text: text.trim(),
        patient_id: patientId.trim() || undefined,
      };
      const result = await apiPost<TriageResult>("/api/triage", body);

      // Write full result to Firestore so other clinicians see it in the queue
      await setDoc(doc(db, "triage_sessions", result.encounter_id), {
        ...result,
        raw_input: text.trim(),
        patient_id: patientId.trim() || "unassigned",
        status: result.circuit_breaker_tripped ? "pending" : "pending",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        submitted_by: user?.email ?? "unknown",
      });

      onResult(result);
      toast("Triage completed successfully", "success");
      setText("");
      setPatientId("");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Submission failed", "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
      <div>
        <label htmlFor="patient-id" className="block text-sm font-medium text-gray-700">
          Patient ID (optional)
        </label>
        <input
          id="patient-id"
          type="text"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          placeholder="e.g. pat-001"
          className="mt-1 block w-full rounded-md border border-border px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
      <div>
        <label htmlFor="encounter-text" className="block text-sm font-medium text-gray-700">
          Encounter Text
        </label>
        <textarea
          id="encounter-text"
          required
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe the patient encounter (symptoms, vitals, history, medications)..."
          className="mt-1 block w-full rounded-md border border-border px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <p className="mt-1 text-xs text-muted">{text.length} characters</p>
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-50"
      >
        {submitting ? "Processing..." : "Submit Encounter"}
      </button>
    </form>
  );
}
