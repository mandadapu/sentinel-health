# Sentinel-Health Orchestrator

Clinical triage automation for mid-size hospitals (50-500 encounters/day) using a multi-agent LangGraph pipeline with HIPAA-compliant GCP infrastructure.

## Architecture

- **Backend**: Python 3.12, FastAPI, LangGraph — multi-agent triage pipeline (Extractor → Reasoner → Sentinel)
- **Sidecar**: Python + Rust-compiled regex — PII detection, FHIR validation, PHI stripping
- **Frontend**: React SPA with SSE for real-time triage result streaming
- **Infra**: Terraform on GCP (Cloud Run, Cloud SQL/pgvector, Firestore, Pub/Sub, BigQuery, KMS)

## Project Structure

```
infra/          — Terraform modules + environments (dev/staging/prod)
backend/        — FastAPI orchestrator + approval worker
sidecar/        — Validator sidecar (Rust regex + Python)
frontend/       — React dashboard
```

## Key Conventions

- **Terraform**: Environment-per-directory pattern (`infra/environments/{env}/`), shared modules in `infra/modules/`
- **Python**: Python 3.12, use `pyproject.toml`, format with ruff, type hints required
- **All resources**: Must include labels `compliance=hipaa`, `environment={env}`, `managed_by=terraform`
- **Secrets**: Never in Terraform state or code. Use Secret Manager with out-of-band value population.
- **Region**: All GCP resources in `us-central1`

## Common Commands

```bash
make tf-validate    # terraform init -backend=false && terraform validate
make tf-plan        # terraform plan (requires GCP credentials)
make tf-fmt         # terraform fmt -recursive
make dev-up         # docker-compose up (local dev)
```

## Discovery Doc

Full architecture decisions and requirements in `docs/sentinel-health-discovery.md`
