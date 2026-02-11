variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for networking resources"
}

variable "env" {
  type        = string
  description = "Environment name (e.g. dev, staging, prod)"
}
