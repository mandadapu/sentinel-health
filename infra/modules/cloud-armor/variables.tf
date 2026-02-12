variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "env" {
  description = "Environment name"
  type        = string
}

variable "rate_limit_requests_per_interval" {
  description = "Number of requests allowed per interval before rate limiting"
  type        = number
  default     = 500
}

variable "rate_limit_interval_sec" {
  description = "Rate limit interval in seconds"
  type        = number
  default     = 60
}

variable "enable_geo_restriction" {
  description = "Enable US-only geo-restriction (recommended for HIPAA prod)"
  type        = bool
  default     = false
}
