variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "env" {
  description = "Environment name"
  type        = string
}

variable "vpc_connector_id" {
  description = "VPC Access Connector ID for private networking"
  type        = string
}

variable "orchestrator_sa_email" {
  description = "Orchestrator service account email"
  type        = string
}

variable "approval_worker_sa_email" {
  description = "Approval worker service account email"
  type        = string
}

variable "audit_consumer_sa_email" {
  description = "Audit consumer service account email"
  type        = string
}

variable "cloudsql_instance_connection" {
  description = "Cloud SQL instance connection name for Cloud SQL Auth Proxy"
  type        = string
}

variable "orchestrator_image" {
  description = "Container image for the orchestrator"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "sidecar_image" {
  description = "Container image for the validator sidecar"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "approval_worker_image" {
  description = "Container image for the approval worker"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "audit_consumer_image" {
  description = "Container image for the audit consumer"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "frontend_image" {
  description = "Container image for the frontend"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

# ---------------------------------------------------------------------------
# Scaling
# ---------------------------------------------------------------------------

variable "orchestrator_min_instances" {
  description = "Minimum instance count for orchestrator (use 1+ in prod to avoid cold starts)"
  type        = number
  default     = 0
}

variable "orchestrator_max_instances" {
  description = "Maximum instance count for orchestrator"
  type        = number
  default     = 10
}

variable "worker_min_instances" {
  description = "Minimum instance count for workers (approval-worker, audit-consumer)"
  type        = number
  default     = 0
}

variable "worker_max_instances" {
  description = "Maximum instance count for workers"
  type        = number
  default     = 5
}

# ---------------------------------------------------------------------------
# Model configuration (passed as env vars to orchestrator)
# ---------------------------------------------------------------------------

variable "classifier_model" {
  description = "Anthropic model for classification"
  type        = string
  default     = "claude-haiku-4-5-20241022"
}

variable "sentinel_model" {
  description = "Anthropic model for sentinel checks"
  type        = string
  default     = "claude-haiku-4-5-20241022"
}

variable "hallucination_threshold" {
  description = "Hallucination detection threshold"
  type        = string
  default     = "0.15"
}

variable "confidence_threshold" {
  description = "Minimum confidence threshold"
  type        = string
  default     = "0.85"
}

variable "cloudsql_dsn" {
  description = "PostgreSQL DSN for Cloud SQL (e.g. postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance)"
  type        = string
  sensitive   = true
}

variable "bigquery_dataset" {
  description = "BigQuery dataset ID for audit trail"
  type        = string
  default     = "sentinel_audit"
}

variable "cors_allowed_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
  default     = "http://localhost:3000"
}

variable "restrict_ingress" {
  description = "Restrict Cloud Run ingress to internal + Cloud Load Balancing only"
  type        = bool
  default     = false
}
