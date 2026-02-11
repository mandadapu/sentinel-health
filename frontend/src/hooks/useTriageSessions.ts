import { useEffect, useState } from "react";
import {
  collection,
  onSnapshot,
  orderBy,
  query,
  type Timestamp,
} from "firebase/firestore";
import { db } from "@/services/firebase";
import { apiPost } from "@/services/api";
import type { ApprovalStatus, TriageSession } from "@/types/triage";

function parseTimestamp(ts: Timestamp | string | undefined): string {
  if (!ts) return new Date().toISOString();
  if (typeof ts === "string") return ts;
  return ts.toDate().toISOString();
}

export function useTriageSessions(collectionName = "triage_sessions") {
  const [sessions, setSessions] = useState<TriageSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const q = query(
      collection(db, collectionName),
      orderBy("updated_at", "desc"),
    );

    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const data = snapshot.docs.map((d) => {
          const raw = d.data();
          return {
            ...raw,
            encounter_id: d.id,
            created_at: parseTimestamp(raw.created_at as Timestamp | string),
            updated_at: parseTimestamp(raw.updated_at as Timestamp | string),
          } as TriageSession;
        });
        setSessions(data);
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
    );

    return unsubscribe;
  }, [collectionName]);

  async function updateApproval(
    encounterId: string,
    status: ApprovalStatus,
    reviewerEmail: string,
    notes: string = "",
  ) {
    await apiPost("/api/approve", {
      encounter_id: encounterId,
      status,
      reviewer_id: reviewerEmail,
      notes,
    });
  }

  return { sessions, loading, error, updateApproval };
}
