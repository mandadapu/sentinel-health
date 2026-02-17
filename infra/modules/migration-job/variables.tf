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

variable "orchestrator_image" {
  description = "Container image for the orchestrator (contains Alembic + migrations)"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "orchestrator_sa_email" {
  description = "Service account email (needs Cloud SQL client + Secret Manager access)"
  type        = string
}

variable "vpc_connector_id" {
  description = "VPC Access Connector ID for private Cloud SQL access"
  type        = string
}

variable "cloudsql_instance_connection" {
  description = "Cloud SQL instance connection name for Auth Proxy"
  type        = string
}
