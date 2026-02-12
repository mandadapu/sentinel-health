# Discovery Summary: Sentinel-Health Orchestrator

## Overview

The Sentinel-Health Orchestrator automates clinical triage and documentation for mid-size hospital systems (50–500 encounters/day) using a multi-agent LangGraph pipeline with Zero-Trust security. Discovery was conducted through sequential requirements gathering followed by six architecture decisions, covering model routing, execution model, safety validation, RAG, frontend, and observability.

---

## Requirements Baseline

| Dimension | Decision | Rationale |
|---|---|---|
| Deployment target | Mid-size hospital, 50–500 encounters/day | Sufficient volume to validate routing economics, manageable compliance scope |
| LLM strategy | Multi-provider intelligent routing | Haiku classifier → confidence-based escalation, applied to clinical categories |
| HITL model | Queue-based batch approvals | Clinicians review in dashboard, not interrupted per-encounter |
| Data ingestion | Hybrid — standalone MVP, EHR hooks designed in | Avoid EHR integration blocking MVP, but Hexagonal Architecture ports ready |
| Latency | Real-time per-encounter (< 5s target) | Clinicians expect immediate feedback on submission |
| BAA model | Dual — GCP BAA + direct Anthropic BAA | Enables direct Claude API access (extended thinking, full feature set) |
| Database | Dual — Firestore (state) + Cloud SQL/pgvector (RAG + audit) | Each database optimized for its workload, no forced compromise |
| Validator sidecar | Python + Rust-compiled regex | Python ecosystem compatibility with wire-speed PII scanning |
| Knowledge source | Layered — hospital-curated base + FHIR public guidelines fallback | Working system from day one, hospital protocols override when present |

---

## Architectural Decisions

### ADR-1: Multi-Model Routing — Haiku Classifier with Clinical Escalation

- **Chosen:** Haiku classifier + confidence-based escalation (adapted from existing router pattern)
- **Rationale:** Proven pattern with demonstrated 80%+ cost savings. Reusing existing classifier architecture reduces development risk.
- **Clinical Adaptations Required:**
  - Clinical classification categories replace general-purpose ones: `routine_vitals`, `symptom_assessment`, `medication_review`, `acute_presentation`, `critical_emergency`, `mental_health`, `pediatric`, `surgical_consult`, `chronic_management`, `diagnostic_interpretation`
  - Conservative threshold tuning: escalation trigger raised from 55% → 70% confidence minimum for any clinical routing
  - Safety override: any encounter containing keywords from a critical-symptom dictionary (chest pain, stroke symptoms, anaphylaxis, etc.) bypasses classifier → routes directly to Opus regardless of confidence
  - All classifier misroutes are logged to BigQuery with human-corrected labels for fine-tuning

**Model Assignment by Clinical Category:**

| Category | Default Model | Escalation Threshold | Safety Override |
|---|---|---|---|
| routine_vitals | Haiku 4.5 | < 65% → Sonnet | No |
| chronic_management | Haiku 4.5 | < 60% → Sonnet | No |
| symptom_assessment | Sonnet 4.5 | < 55% → Opus | Yes — critical symptoms |
| medication_review | Sonnet 4.5 | < 50% → Opus | Yes — drug interactions |
| diagnostic_interpretation | Sonnet 4.5 | < 45% → Opus | Yes — abnormal results |
| acute_presentation | Opus 4.6 | N/A (always Opus) | Yes |
| critical_emergency | Opus 4.6 | N/A (always Opus) | Yes |
| mental_health | Opus 4.6 | N/A (always Opus) | Yes |
| pediatric | Opus 4.6 | N/A (always Opus) | Yes |
| surgical_consult | Opus 4.6 | N/A (always Opus) | Yes |

**Estimated Cost Impact:**
- At 500 encounters/day with typical distribution (40% routine, 35% moderate, 25% complex): ~65–75% savings vs. all-Opus baseline
- Classifier overhead: ~$0.015/day (negligible)

---

### ADR-2: LangGraph Execution — Pub/Sub Bridge

- **Chosen:** Synchronous LangGraph for triage decision → Pub/Sub publish → async consumer for HITL + writeback
- **Rationale:** Clean separation of real-time clinical logic from approval lifecycle. Pub/Sub provides dead-letter queues (critical for HIPAA audit of failed approvals), automatic retry, and natural decoupling.
- **Implications:**
  - **Sync Graph (Cloud Run — Orchestrator):** Receives encounter → runs Extractor → Reasoner → Sentinel → returns triage result to caller → publishes `TriageCompleted` event to Pub/Sub
  - **Async Consumer (Cloud Run — Approval Worker):** Subscribes to `TriageCompleted` → writes to approval queue in Firestore → waits for clinician action → on approval, writes back to Cloud SQL + publishes `TriageApproved` event
  - **Dead Letter Topic:** `TriageCompleted-dlq` — any message that fails processing 5x lands here. Alerts via Cloud Monitoring. HIPAA requires these are investigated within 24 hours. See `docs/runbooks/dlq-investigation.md` for the full investigation procedure.
  - **Message Schema:**

```json
{
  "encounter_id": "uuid",
  "patient_id": "encrypted-ref",
  "triage_result": {
    "level": "Urgent",
    "confidence": 0.91,
    "reasoning_summary": "...",
    "model_used": "claude-sonnet-4-5-20250929",
    "routing_reason": "Category: symptom_assessment, confidence 72%"
  },
  "sentinel_check": {
    "passed": true,
    "hallucination_score": 0.08,
    "confidence_score": 0.91
  },
  "timestamp": "ISO-8601",
  "audit_ref": "firestore-doc-id"
}
```

---

### ADR-3: Dual-Layer Validation — Sidecar + Sentinel

- **Chosen:** Rust-regex Python sidecar for fast structural checks on every LLM call + Sentinel agent for deep clinical validation once at end
- **Rationale:** Defense in depth without exceeding latency budget. Structural failures caught at wire speed (~2–5ms), clinical plausibility assessed once at the decision boundary.

**Layer 1 — Sidecar (Every LLM Response):**

| Check | Method | Latency | Action on Failure |
|---|---|---|---|
| PII detection | Rust-compiled regex (SSN, MRN, phone, email patterns) | ~1ms | Mask in-place, flag in `compliance_flags` |
| FHIR schema validation | JSON Schema validator (FHIR R4) | ~2ms | Reject response, retry LLM call (max 2 retries) |
| PHI in logs | Regex scan of any data destined for audit trail | ~1ms | Strip before write, log redaction event |
| Token limit guard | Count output tokens vs. expected range | <1ms | Truncate + flag if response is suspiciously short/long |

**Layer 2 — Sentinel Agent (End of Pipeline):**

| Check | Method | Latency | Action on Failure |
|---|---|---|---|
| Hallucination score | LLM self-evaluation prompt (Haiku — cheap) | ~80–130ms | If > 0.15 → circuit break → `Manual_Review_Required` |
| Clinical confidence | Extracted from Reasoner output | ~0ms (already computed) | If < 0.85 → circuit break |
| Cross-reference | Compare triage level vs. extracted vitals/symptoms | ~50ms (deterministic rules) | Flag contradictions (e.g., "Routine" with BP > 180) |
| Medication safety | Check prescribed meds against known interaction database | ~20ms (Cloud SQL lookup) | Flag interactions → auto-escalate triage level |

**Total Added Latency:** ~10–20ms (sidecar, per-node × 3 nodes) + ~150–200ms (Sentinel, once) = ~180–260ms total validation overhead

---

### ADR-4: RAG — pgvector in Cloud SQL with Layered Knowledge

- **Chosen:** pgvector cosine similarity retrieval in Cloud SQL, with hospital-curated protocols as primary source and FHIR ClinicalGuideline resources as fallback
- **Rationale:** Consolidates RAG + audit in a single database. pgvector handles the scale (< 100K protocol documents at this hospital size) easily. Layered knowledge gives hospitals a working system from day one.

**Schema Design:**

```sql
-- Clinical protocols table with vector embeddings
CREATE TABLE clinical_protocols (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- text-embedding-004 from Vertex AI
    source_type TEXT NOT NULL CHECK (source_type IN ('hospital_curated', 'fhir_public')),
    specialty TEXT,           -- e.g., 'cardiology', 'emergency', 'pediatrics'
    effective_date DATE,
    expiry_date DATE,
    version INT DEFAULT 1,
    hospital_id UUID,         -- NULL for public FHIR guidelines
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Retrieval priority: hospital-curated first, then public
CREATE INDEX idx_protocols_embedding ON clinical_protocols
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

CREATE INDEX idx_protocols_source ON clinical_protocols (source_type, specialty);

-- Audit log table (queryable from dashboard)
CREATE TABLE encounter_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL,
    patient_id_encrypted TEXT NOT NULL,  -- Encrypted reference
    node_name TEXT NOT NULL,             -- 'extractor', 'reasoner', 'sentinel'
    model_used TEXT NOT NULL,
    input_tokens INT,
    output_tokens INT,
    cost_usd DECIMAL(10, 8),
    reasoning_snapshot JSONB,            -- Full agent thought process
    compliance_flags TEXT[],
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_encounter ON encounter_audit (encounter_id);
CREATE INDEX idx_audit_created ON encounter_audit (created_at DESC);

-- HITL approval queue
CREATE TABLE triage_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL UNIQUE,
    triage_level TEXT NOT NULL,
    confidence_score DECIMAL(4, 3),
    reasoning_summary TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'escalated')),
    clinician_id UUID,
    clinician_notes TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    sla_deadline TIMESTAMPTZ  -- For tracking approval turnaround
);

CREATE INDEX idx_approvals_status ON triage_approvals (status, submitted_at);
```

**Retrieval Strategy:**

```python
async def retrieve_protocols(query_embedding, specialty=None, hospital_id=None, top_k=5):
    """
    Layered retrieval: hospital-curated first, backfill with public FHIR.
    """
    # Priority 1: Hospital-curated protocols
    hospital_results = await db.fetch("""
        SELECT id, title, content, 1 - (embedding <=> $1) AS similarity
        FROM clinical_protocols
        WHERE source_type = 'hospital_curated'
          AND hospital_id = $2
          AND ($3::text IS NULL OR specialty = $3)
          AND (expiry_date IS NULL OR expiry_date > NOW())
        ORDER BY embedding <=> $1
        LIMIT $4
    """, query_embedding, hospital_id, specialty, top_k)

    # Priority 2: Backfill with public FHIR guidelines if needed
    remaining = top_k - len(hospital_results)
    if remaining > 0:
        public_results = await db.fetch("""
            SELECT id, title, content, 1 - (embedding <=> $1) AS similarity
            FROM clinical_protocols
            WHERE source_type = 'fhir_public'
              AND ($2::text IS NULL OR specialty = $2)
              AND (expiry_date IS NULL OR expiry_date > NOW())
            ORDER BY embedding <=> $1
            LIMIT $3
        """, query_embedding, specialty, remaining)
        hospital_results.extend(public_results)

    return hospital_results
```

---

### ADR-5: React SPA with SSE for Real-Time Dashboard

- **Chosen:** React SPA (separate deployment) with Server-Sent Events for real-time triage result push
- **Rationale:** Production-grade frontend from day one. SSE is Cloud Run compatible (works within HTTP request/response), simpler than WebSocket, and sufficient for one-way push of triage results.
- **Implications:**
  - **Frontend Deployment:** Cloud Run (static build served via nginx) or Firebase Hosting (CDN, simpler)
  - **Auth:** Firebase Auth with Cloud Identity Platform — supports hospital SSO (SAML/OIDC) for HIPAA
  - **SSE Endpoint:** `GET /api/stream/triage-results` — Cloud Run Orchestrator maintains SSE connection, pushes new results as they're written to Firestore
  - **API Layer:** FastAPI serves both the LangGraph submission endpoint and the SSE stream
  - **MVP Scope:** Approval queue (list/filter/batch approve), triage detail view (reasoning chain from Firestore), basic analytics (encounters/day, model distribution, avg approval time)
  - **Phase 2 Additions:** Multimodal viewer (insurance card images, handwritten notes), EHR integration status panel, protocol management admin

**SSE Implementation Pattern:**

```python
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore

app = FastAPI()

async def triage_event_generator(hospital_id: str):
    """Stream new triage results via Firestore watch."""
    db = firestore.AsyncClient()
    query = (db.collection("triage_sessions")
             .where("hospital_id", "==", hospital_id)
             .where("status", "==", "pending_review")
             .order_by("created_at", direction="DESCENDING")
             .limit(50))

    async for snapshot in query.on_snapshot_async():
        for change in snapshot.changes:
            if change.type.name == "ADDED":
                yield {
                    "event": "new_triage",
                    "data": change.document.to_dict()
                }

@app.get("/api/stream/triage-results")
async def stream_triage(hospital_id: str):
    return EventSourceResponse(triage_event_generator(hospital_id))
```

---

### ADR-6: Dual-Write Audit — Firestore (Real-Time) + BigQuery (Compliance)

- **Chosen:** Synchronous write to Firestore after each LangGraph node (for dashboard), async Pub/Sub → BigQuery pipeline (for compliance queries)
- **Rationale:** Firestore writes are fast (~5–10ms), keeping the pipeline within real-time budget. BigQuery provides the compliance-grade, queryable archive for HIPAA auditors. Eventual consistency on the BigQuery side is acceptable for retrospective audits.

**Audit Data Flow:**

```
LangGraph Node Completes
    │
    ├──► Firestore (sync, ~5-10ms)
    │       └── Dashboard reads via onSnapshot / SSE
    │
    └──► Pub/Sub topic: "audit-events" (async, fire-and-forget)
            └── Cloud Run consumer → BigQuery streaming insert
                    └── HIPAA auditor queries via BigQuery SQL
```

**Firestore Audit Document Structure:**

```json
{
  "encounter_id": "uuid",
  "node": "reasoner",
  "model": "claude-sonnet-4-5-20250929",
  "routing_decision": {
    "category": "symptom_assessment",
    "confidence": 0.72,
    "reason": "Category default: sonnet"
  },
  "input_summary": "Patient presents with...",
  "output_summary": "Triage level: Urgent...",
  "tokens": { "in": 1250, "out": 480 },
  "cost_usd": 0.0108,
  "compliance_flags": ["PII_REDACTED", "FHIR_VALID"],
  "sentinel_check": null,
  "duration_ms": 823,
  "timestamp": "2025-08-15T14:32:01.234Z"
}
```

**BigQuery Table Schema:**

```sql
CREATE TABLE sentinel_health.audit_trail (
    encounter_id STRING NOT NULL,
    node_name STRING NOT NULL,
    model_used STRING NOT NULL,
    routing_category STRING,
    routing_confidence FLOAT64,
    input_tokens INT64,
    output_tokens INT64,
    cost_usd FLOAT64,
    reasoning_snapshot JSON,
    compliance_flags ARRAY<STRING>,
    sentinel_hallucination_score FLOAT64,
    sentinel_confidence_score FLOAT64,
    circuit_breaker_tripped BOOL,
    duration_ms INT64,
    created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY encounter_id, node_name;
```

---

## System Architecture — Complete View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REACT SPA (Firebase Hosting)                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Encounter Submit │  │ Approval Queue   │  │ Analytics Dashboard     │   │
│  │ (POST /api/     │  │ (SSE stream +    │  │ (model dist, cost,     │   │
│  │  triage)        │  │  batch approve)  │  │  approval turnaround)  │   │
│  └────────┬────────┘  └────────▲─────────┘  └──────────────────────────┘   │
│           │                    │ SSE: /api/stream/triage-results            │
└───────────┼────────────────────┼───────────────────────────────────────────┘
            │ HTTPS              │
            ▼                    │
┌───────────────────────────────────────────────────────────────────────────┐
│                    CLOUD RUN — ORCHESTRATOR (Python/FastAPI)               │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    LANGGRAPH — SYNC TRIAGE PIPELINE                 │  │
│  │                                                                     │  │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐                │  │
│  │  │ EXTRACTOR  │───▶│  REASONER  │───▶│  SENTINEL  │                │  │
│  │  │            │    │            │    │  (Clinical) │                │  │
│  │  │ Haiku/     │    │ Sonnet/    │    │  Halluc.   │                │  │
│  │  │ Sonnet     │    │ Opus       │    │  check +   │                │  │
│  │  │ (routed)   │    │ (routed)   │    │  confidence│                │  │
│  │  └──────┬─────┘    └──────┬─────┘    └──────┬─────┘                │  │
│  │         │                 │                  │                       │  │
│  │    ┌────▼─────────────────▼──────────────────▼────┐                │  │
│  │    │        VALIDATOR SIDECAR (mTLS)               │                │  │
│  │    │  Rust-regex PII scan │ FHIR schema validate  │                │  │
│  │    │  PHI redaction       │ Token limit guard      │                │  │
│  │    └──────────────────────────────────────────────┘                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐   │
│  │ HAIKU CLASSIFIER │  │ ROUTING ENGINE   │  │ SSE STREAM ENDPOINT   │   │
│  │ (clinical cats)  │─▶│ (confidence +    │  │ (Firestore onSnapshot │   │
│  │                  │  │  safety override)│  │  → push to React)     │   │
│  └──────────────────┘  └──────────────────┘  └───────────────────────┘   │
│                                                                           │
│  On triage complete ──► Pub/Sub: "triage-completed"                      │
│  On each node ────────► Firestore (sync) + Pub/Sub: "audit-events"       │
└───────────────────────────────────────────────────────────────────────────┘
            │                              │
            ▼                              ▼
┌───────────────────────┐    ┌──────────────────────────────────────────────┐
│  PUB/SUB TOPICS       │    │  DATA LAYER                                  │
│                       │    │                                              │
│  triage-completed ────┼───▶│  FIRESTORE (us-central1)                    │
│    └─ DLQ             │    │    ├── triage_sessions/{id}                  │
│                       │    │    ├── audit_trail/{encounter}/{node}        │
│  audit-events ────────┼──┐ │    └── approval_queue/{id}                  │
│    └─ DLQ             │  │ │                                              │
│                       │  │ │  CLOUD SQL + pgvector (us-central1, CMEK)   │
│  triage-approved ─────┼──┤ │    ├── clinical_protocols (+ embeddings)    │
│    └─ DLQ             │  │ │    ├── encounter_audit                      │
└───────────────────────┘  │ │    └── triage_approvals                     │
                           │ │                                              │
                           │ │  BIGQUERY (us-central1)                     │
                           └▶│    └── sentinel_health.audit_trail          │
                             │        (partitioned by date, clustered by   │
                             │         encounter_id)                        │
                             └──────────────────────────────────────────────┘
                                               │
┌──────────────────────────────────────────────┼───────────────────────────┐
│  CLOUD RUN — APPROVAL WORKER                 │                           │
│                                              ▼                           │
│  Subscribes to "triage-completed"    Reads from Firestore                │
│  ├── Writes to approval queue        on clinician action:                │
│  ├── Waits for clinician approval    ├── Validates approval              │
│  ├── On approve → write to Cloud SQL ├── Publishes "triage-approved"     │
│  └── On reject → flag for re-triage  └── Updates audit trail             │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL INTEGRATIONS                                                    │
│                                                                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │ VERTEX AI        │  │ ANTHROPIC API    │  │ EHR FHIR ENDPOINTS    │  │
│  │ Model Garden     │  │ (Direct, BAA)    │  │ (Phase 2)             │  │
│  │ ├── Gemini       │  │ ├── Claude Opus  │  │ ├── Epic SMART-on-    │  │
│  │ ├── Embeddings   │  │ ├── Claude Sonnet│  │ │   FHIR (OAuth)      │  │
│  │ │   (text-004)   │  │ └── Claude Haiku │  │ └── Cerner R4 API    │  │
│  │ └── (GCP BAA)    │  │     (Dual BAA)   │  │     (Phase 2)        │  │
│  └─────────────────┘  └──────────────────┘  └────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ SECURITY & COMPLIANCE                                            │    │
│  │ ├── Cloud KMS (CMEK for Cloud SQL encryption at rest)            │    │
│  │ ├── VPC Service Controls (us-central1 perimeter)                 │    │
│  │ ├── Cloud IAM Workload Identity Federation (agent SAs)           │    │
│  │ ├── mTLS between Orchestrator ↔ Sidecar                         │    │
│  │ ├── Cloud Monitoring + Alerting (DLQ depth, circuit breaker)     │    │
│  │ └── Secret Manager (API keys, DB credentials)                    │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Conflict Analysis

| Potential Conflict | Resolution |
|---|---|
| Firestore + Cloud SQL dual-write consistency | Firestore is source of truth for real-time state; Cloud SQL is source of truth for compliance. Encounter ID links them. Reconciliation job runs daily. |
| SSE via Cloud Run timeout (max 60 min) | Client-side reconnection with `Last-Event-ID`. Cloud Run gen2 supports streaming responses. |
| Dual BAA complicates data flow | PHI only flows to Anthropic API for LLM inference (encrypted in transit). No PHI stored by Anthropic. Firestore + Cloud SQL hold all persistent PHI under GCP BAA. Document this in BAA addendum. |
| No-training policy for PHI data | Anthropic API operates under a zero-retention, no-training policy — PHI sent for inference is not stored beyond the request lifecycle and is never used to train or fine-tune public models. This is contractually enforced via the Anthropic BAA and further guaranteed by Anthropic's API data usage policy (API inputs/outputs are not used for model training). Vertex AI Gemini embeddings are similarly covered under the GCP BAA with Google's no-training commitment for BAA-covered services. Verify no-training clauses during BAA signing and re-verify annually during compliance reviews. |
| Haiku classifier accuracy for clinical categories | Conservative thresholds (70% min confidence) + critical-symptom safety override + human correction feedback loop to BigQuery for continuous improvement. |
| Real-time latency budget with dual-layer validation | Budget: Classifier (~100ms) + Sidecar (3 × ~5ms) + LLM calls (~800–2200ms per node) + Sentinel (~200ms) + Firestore write (~10ms) ≈ 1.5–4.5s total. Within "seconds" target. |

---

## MVP Scope (Month 1–3)

### In Scope
- LangGraph pipeline: Extractor → Reasoner → Sentinel (3 nodes)
- Multi-model routing with clinical classifier
- Validator sidecar with Rust-regex PII scanning + FHIR validation
- Pub/Sub bridge for async HITL
- React SPA: encounter submission, approval queue, triage detail view
- SSE for real-time updates
- Dual-write audit trail (Firestore + BigQuery)
- pgvector RAG with layered clinical protocols
- Cloud SQL schema (protocols, audit, approvals)
- Terraform IaC for GCP resources (Cloud Run, Pub/Sub, Firestore, Cloud SQL, KMS)
- HIPAA security controls (CMEK, VPC, IAM, mTLS)

### Out of Scope (Phase 2)
- Multimodal extraction (insurance cards, handwritten notes via Vertex AI Vision)
- EHR integration (Epic/Cerner FHIR APIs, SMART-on-FHIR OAuth)
- Advanced analytics dashboard
- Protocol management admin interface
- Automated classifier retraining from human correction labels
- Multi-hospital tenancy

---

## Claude Code Build Prompts (Updated)

### Prompt 1 — Infrastructure (Terraform)
```
Using Terraform, initialize a HIPAA-compliant GCP project in us-central1. Create:
1. VPC with Private Google Access, no public IPs
2. Cloud Run service "orchestrator" (Python 3.12, 2 containers: main + sidecar)
3. Cloud Run service "approval-worker" (Python 3.12)
4. Cloud SQL PostgreSQL 15 with pgvector extension, CMEK via Cloud KMS
5. Firestore in Native mode
6. Pub/Sub topics: triage-completed, audit-events, triage-approved (each with DLQ)
7. BigQuery dataset: sentinel_health with audit_trail table (partitioned by date)
8. Cloud KMS keyring with keys for Cloud SQL CMEK
9. Service accounts with least-privilege IAM for each Cloud Run service
10. VPC Connector for Cloud Run → Cloud SQL private access
11. Secret Manager for API keys (Anthropic, Vertex AI)
```

### Prompt 2 — LangGraph Pipeline
```
Implement a LangGraph StateGraph in the orchestrator container:
- State: AgentState TypedDict with fields: raw_input, fhir_data, clinical_context,
  triage_decision, audit_trail, compliance_flags, routing_metadata
- Nodes: extractor, reasoner, sentinel
- Each node calls a model selected by the routing engine (Haiku classifier →
  confidence-based escalation with clinical safety overrides)
- After each node: sync write audit snapshot to Firestore, async publish to
  Pub/Sub audit-events topic
- Sentinel node: check hallucination_score > 0.15 OR confidence < 0.85 →
  circuit break to Manual_Review_Required
- On pipeline complete: publish TriageCompleted to Pub/Sub triage-completed topic
- All data exchange uses FHIR R4 schema (validated by sidecar)
```

### Prompt 3 — Validator Sidecar
```
Inside the sidecar container, implement a FastAPI middleware:
1. Rust-compiled regex (via rure-python or regex crate via PyO3) for PII detection:
   SSN, MRN, phone, email, DOB patterns
2. FHIR R4 JSON Schema validation for all LLM outputs
3. PHI stripping from any data destined for audit/logging paths
4. Token count validation (flag anomalous response lengths)
5. mTLS configuration for orchestrator ↔ sidecar communication
6. Health check endpoint for Cloud Run
```

### Prompt 4 — React Dashboard
```
Create a React SPA with:
1. Firebase Auth integration (email + SAML SSO stub for hospitals)
2. Encounter submission form (text input, file upload placeholder for Phase 2)
3. Approval queue: filterable table (pending/approved/rejected), batch select,
   bulk approve/reject with clinician notes
4. Triage detail view: reasoning chain from Firestore, model used, confidence,
   compliance flags, Sentinel results
5. SSE client connecting to /api/stream/triage-results for real-time updates
6. Basic analytics: encounters today, model distribution pie chart, avg approval time
7. Deploy config for Firebase Hosting
```

---

## Verification Checklist

- [x] mTLS between Orchestrator and Sidecar (ADR-3)
- [x] CMEK for Cloud SQL data at rest (ADR-6, Security)
- [x] Circuit Breaker is deterministic: hallucination > 0.15 OR confidence < 0.85 (ADR-3)
- [x] Pub/Sub dead-letter queues for all topics (ADR-2)
- [x] All compute and storage in us-central1 (Infrastructure)
- [x] Dual BAA documented — GCP + Anthropic (Requirements)
- [x] PHI never stored by Anthropic — only in-transit for inference (Conflict Analysis)
- [x] No-training clause — Anthropic API and Vertex AI BAA-covered services contractually prohibited from using PHI for model training (Conflict Analysis)
- [x] Write-ahead audit to Firestore before pipeline proceeds (ADR-6)
- [x] Safety override bypasses classifier for critical symptoms (ADR-1)
- [x] EHR integration hooks designed via Hexagonal Architecture ports (Phase 2 ready)
