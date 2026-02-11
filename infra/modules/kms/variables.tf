variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "env" {
  type = string
}

variable "project_number" {
  description = "GCP project number for Cloud SQL service agent reference"
  type        = string
}
