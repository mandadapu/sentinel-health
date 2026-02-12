locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

resource "google_bigquery_dataset" "sentinel_health" {
  dataset_id  = "sentinel_health_${var.env}"
  project     = var.project_id
  location    = var.region
  description = "Sentinel-Health audit and compliance data"
  labels      = local.labels

  delete_contents_on_destroy = false
}

resource "google_bigquery_table" "audit_trail" {
  dataset_id          = google_bigquery_dataset.sentinel_health.dataset_id
  table_id            = "audit_trail"
  project             = var.project_id
  description         = "HIPAA-compliant audit trail for all pipeline executions"
  deletion_protection = true
  labels              = local.labels

  schema = file("${path.module}/schemas/audit_trail.json")

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  clustering = ["encounter_id", "node_name"]
}

resource "google_bigquery_table" "classifier_feedback" {
  dataset_id          = google_bigquery_dataset.sentinel_health.dataset_id
  table_id            = "classifier_feedback"
  project             = var.project_id
  description         = "Classifier misroute corrections from clinician review — used for fine-tuning"
  deletion_protection = true
  labels              = local.labels

  schema = file("${path.module}/schemas/classifier_feedback.json")

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }

  clustering = ["original_category", "corrected_category"]
}
