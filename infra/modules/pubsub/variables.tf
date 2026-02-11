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
