variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for secret replication"
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
