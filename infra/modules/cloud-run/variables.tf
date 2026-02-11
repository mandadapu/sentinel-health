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
