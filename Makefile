.PHONY: tf-validate tf-plan tf-fmt tf-init dev-up dev-down lint

ENV ?= dev
TF_DIR = infra/environments/$(ENV)

# Terraform
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

# Local dev
dev-up:
	docker-compose up -d

dev-down:
	docker-compose down

# Linting
lint: tf-fmt
	@echo "Linting complete"
