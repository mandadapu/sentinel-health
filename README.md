# Sentinel-Health Orchestrator

Clinical triage automation for mid-size hospitals (50-500 encounters/day). A multi-agent LangGraph pipeline with HIPAA-compliant GCP infrastructure automates clinical triage decisions with human-in-the-loop approval.

## Architecture

```
React SPA ──HTTPS──> Global LB + Cloud Armor ──> Cloud Run (Orchestrator)
                                                       │
                            ┌──────────────────────────┤
                            │                          │
                     Validator Sidecar          LangGraph Pipeline
                     (PII/FHIR/PHI)        Extractor → Reasoner → Sentinel
                                                       │
                                              Pub/Sub: triage-completed
                                                       │
                                              Cloud Run (Approval Worker)
                                                       │
                                        ┌──────────────┼──────────────┐
                                   Firestore       Cloud SQL       BigQuery
                                  (real-time)    (pgvector RAG)  (audit trail)
```

**Services:**

| Service | Stack | Purpose |
|---|---|---|
| Orchestrator | Python 3.12, FastAPI, LangGraph | Multi-agent triage pipeline with SSE streaming |
| Validator Sidecar | Python + Rust-compiled regex | PII detection, FHIR R4 validation, PHI stripping |
| Approval Worker | Python 3.12, FastAPI | Pub/Sub-driven HITL approval queue |
| Audit Consumer | Python 3.12, FastAPI | Pub/Sub to BigQuery streaming insert |
| Frontend | React, TypeScript, Vite, Tailwind | Clinician dashboard with real-time SSE updates |

## Project Structure

```
backend/            FastAPI orchestrator + LangGraph pipeline
sidecar/            Validator sidecar (Rust regex + Python)
approval-worker/    Pub/Sub-triggered approval service
audit-consumer/     Pub/Sub to BigQuery audit pipeline
frontend/           React clinician dashboard
infra/
  modules/          Terraform modules (reusable)
    bigquery/         Audit trail + classifier feedback tables
    cloud-armor/      WAF: rate limiting, OWASP SQLi/XSS
    cloud-run/        All Cloud Run services (multi-container)
    cloud-sql/        PostgreSQL 15 + pgvector, CMEK
    firestore/        Native mode for real-time state
    iam/              Least-privilege service accounts
    kms/              CMEK keyring for Cloud SQL
    load-balancer/    Global HTTPS LB with managed SSL
    migration-job/    Cloud Run Job for Alembic migrations
    monitoring/       Alert policies + dashboard
    networking/       VPC, subnets, firewall, VPC connector
    pubsub/           3 topics + DLQs with push subscriptions
    secrets/          Secret Manager containers
    vpc-sc/           VPC Service Controls (prod only)
  environments/     Per-environment config
    dev/
    staging/
    prod/
docs/               Discovery doc, runbooks
load-tests/         Locust load testing
certs/              mTLS dev certificates
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- Terraform >= 1.5
- GCP credentials (for cloud deployments)

### Local Development

```bash
# Generate mTLS dev certificates
make gen-certs

# Start all services (Postgres, Redis, etc.)
make dev-up

# Run database migrations
make db-migrate

# Generate protocol embeddings (requires VOYAGE_API_KEY)
make generate-embeddings VOYAGE_API_KEY=your-key

# Run all tests
make test

# Lint all services
make lint
```

### Individual Service Setup

```bash
# Backend
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Sidecar
cd sidecar && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Approval Worker
cd approval-worker && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Audit Consumer
cd audit-consumer && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Frontend
cd frontend && npm install
```

## Infrastructure

All infrastructure is managed via Terraform with environment-per-directory pattern.

```bash
make tf-validate          # Validate Terraform (dev)
make tf-validate ENV=prod # Validate Terraform (prod)
make tf-plan              # Plan changes
make tf-fmt               # Format all Terraform files
```

### Key Infrastructure Features

- **Cloud Armor WAF** -- Rate limiting (500 req/60s), OWASP SQLi+XSS blocking, malicious user-agent filtering, US-only geo-restriction (prod)
- **Global HTTPS Load Balancer** -- Managed SSL, HTTP-to-HTTPS redirect, path-based routing (`/api/*` to orchestrator, `/*` to frontend)
- **Cloud Run Ingress Restriction** -- Services only accept traffic from internal sources + Cloud Load Balancing
- **Cloud Monitoring** -- 5 alert policies (DLQ depth, error rate, p99 latency, Cloud SQL connections/CPU) + dashboard
- **Migration Job** -- Cloud Run Job runs `alembic upgrade head` during deployment (not at service startup)
- **VPC Service Controls** -- Data egress perimeter for prod (opt-in via `access_policy_id`)

### HIPAA Compliance

- CMEK encryption for Cloud SQL via Cloud KMS
- VPC with private networking (no public IPs)
- Pub/Sub DLQs with 24-hour investigation SLA
- Secret Manager for all credentials (out-of-band population)
- All resources labeled `compliance=hipaa`
- PHI stripped from all audit/logging paths via validator sidecar
- Dual BAA: GCP BAA + Anthropic BAA

## Testing

```bash
make test               # All tests
make backend-test       # Backend unit + integration
make sidecar-test       # Sidecar validation tests
make worker-test        # Approval worker tests
make consumer-test      # Audit consumer tests
make frontend-test      # Frontend vitest
make load-test          # Locust headless (10 users, 5 min)
make load-test-ui       # Locust with web UI
```

## Deployment

CI/CD is via GitHub Actions:

- **CI**: Lint + test on PRs (per-service workflows)
- **CD Images**: Build + push Docker images to Artifact Registry on main
- **CD Deploy**: Terraform apply + migration job + health check verification
  - Staging: auto-deploys after image build
  - Prod: manual dispatch with GitHub Environment approval gate

## Multi-Model Routing

The Haiku classifier routes encounters to the appropriate model based on clinical category:

| Category | Default Model | Safety Override |
|---|---|---|
| routine_vitals, chronic_management | Haiku 4.5 | No |
| symptom_assessment, medication_review, diagnostic_interpretation | Sonnet 4.5 | Yes |
| acute_presentation, critical_emergency, mental_health, pediatric, surgical_consult | Opus 4.6 | Yes |

Classifier misroutes are logged to BigQuery (`classifier_feedback` table) with clinician-corrected labels for future fine-tuning.

## Documentation

- **Discovery Doc**: `docs/sentinel-health-discovery.md` -- Full ADRs, architecture, schemas
- **DLQ Runbook**: `docs/runbooks/dlq-investigation.md` -- HIPAA-required investigation procedure
- **CLAUDE.md**: Development conventions and common commands
