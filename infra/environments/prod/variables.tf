variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_number" {
  description = "GCP project number (for service agent references)"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "env" {
  description = "Environment name"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "env must be one of: dev, staging, prod"
  }
}

variable "notification_email" {
  description = "Email address for Cloud Monitoring alert notifications"
  type        = string
}

variable "domain_name" {
  description = "Custom domain for the production load balancer"
  type        = string
  default     = "sentinel-health.example.com"
}
