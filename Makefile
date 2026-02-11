.PHONY: tf-validate tf-plan tf-fmt tf-init tf-lint \
       dev-up dev-down build \
       test backend-test sidecar-test frontend-test worker-test \
       lint backend-lint sidecar-lint worker-lint \
       typecheck gen-certs

ENV ?= dev
TF_DIR = infra/environments/$(ENV)

# ── Terraform ────────────────────────────────────────────────────────────────

tf-init:
	cd $(TF_DIR) && terraform init -backend=false

tf-validate: tf-init
	cd $(TF_DIR) && terraform validate

tf-plan:
	cd $(TF_DIR) && terraform plan -var-file=terraform.tfvars

tf-fmt:
	terraform fmt -recursive infra/

tf-lint:
	cd $(TF_DIR) && tflint --init && tflint --recursive

# ── Testing ──────────────────────────────────────────────────────────────────

test: backend-test sidecar-test frontend-test worker-test

backend-test:
	cd backend && .venv/bin/python -m pytest tests/ -v

sidecar-test:
	cd sidecar && .venv/bin/python -m pytest tests/ -v

frontend-test:
	cd frontend && npx vitest run

worker-test:
	cd approval-worker && .venv/bin/python -m pytest tests/ -v

# ── Linting ──────────────────────────────────────────────────────────────────

lint: tf-fmt backend-lint sidecar-lint worker-lint

backend-lint:
	cd backend && .venv/bin/python -m ruff check src/ tests/

sidecar-lint:
	cd sidecar && .venv/bin/python -m ruff check src/ tests/

worker-lint:
	cd approval-worker && .venv/bin/python -m ruff check src/ tests/

# ── Type Checking ────────────────────────────────────────────────────────────

typecheck:
	cd frontend && npx tsc --noEmit

# ── Docker ───────────────────────────────────────────────────────────────────

build:
	docker-compose build

dev-up:
	docker-compose up -d

dev-down:
	docker-compose down

# ── Certificates ──────────────────────────────────────────────────────────

gen-certs:
	bash certs/generate-dev-certs.sh
