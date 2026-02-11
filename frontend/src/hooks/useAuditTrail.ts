import { useEffect, useState } from "react";
import { collection, getDocs, orderBy, query } from "firebase/firestore";
import { db } from "@/services/firebase";
import type { AuditEntry } from "@/types/triage";

export function useAuditTrail(
  encounterId: string | undefined,
  collectionName = "triage_sessions",
) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!encounterId) {
      setLoading(false);
      return;
    }

    const q = query(
      collection(db, collectionName, encounterId, "audit"),
      orderBy("timestamp", "asc"),
    );

    getDocs(q)
      .then((snapshot) => {
        setEntries(snapshot.docs.map((d) => d.data() as AuditEntry));
      })
      .catch(() => {
        setEntries([]);
      })
      .finally(() => setLoading(false));
  }, [encounterId, collectionName]);

  return { entries, loading };
}
