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

variable "domain_name" {
  description = "Domain name for the managed SSL certificate"
  type        = string
}

variable "frontend_cloud_run_service_name" {
  description = "Name of the frontend Cloud Run service"
  type        = string
}

variable "orchestrator_cloud_run_service_name" {
  description = "Name of the orchestrator Cloud Run service"
  type        = string
}

variable "security_policy_id" {
  description = "Cloud Armor security policy ID to attach to backend services"
  type        = string
  default     = ""
}
