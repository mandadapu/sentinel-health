variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "env" {
  description = "Environment name"
  type        = string
}

variable "approval_worker_sa_email" {
  description = "Service account email for the approval worker (Pub/Sub subscriber)"
  type        = string
}

variable "approval_worker_url" {
  description = "Cloud Run URL for approval-worker push endpoint"
  type        = string
}

variable "audit_consumer_url" {
  description = "Cloud Run URL for audit-consumer push endpoint"
  type        = string
}

variable "audit_consumer_sa_email" {
  description = "Audit consumer service account email"
  type        = string
}
