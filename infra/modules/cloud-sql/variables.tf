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

variable "kms_crypto_key_id" {
  description = "Cloud KMS crypto key ID for CMEK encryption"
  type        = string
}

variable "private_network_self_link" {
  description = "VPC self link for private IP networking"
  type        = string
}

variable "private_ip_range_name" {
  description = "Name of the reserved global address range for VPC peering"
  type        = string
}

variable "tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-custom-2-8192"
}

variable "disk_size_gb" {
  description = "Disk size in GB"
  type        = number
  default     = 20
}

variable "availability_type" {
  description = "HA availability type"
  type        = string
  default     = "REGIONAL"
}
