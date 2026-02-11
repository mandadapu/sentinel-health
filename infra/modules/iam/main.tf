###############################################################################
# Service Accounts
###############################################################################

resource "google_service_account" "orchestrator_sa" {
  project      = var.project_id
  account_id   = "sentinel-${var.env}-orchestrator"
  display_name = "Sentinel Orchestrator (${var.env})"
}

resource "google_service_account" "approval_worker_sa" {
  project      = var.project_id
  account_id   = "sentinel-${var.env}-approval-worker"
  display_name = "Sentinel Approval Worker (${var.env})"
}

###############################################################################
# IAM Role Bindings
###############################################################################

locals {
  orchestrator_roles = [
    "roles/datastore.user",               # Firestore
    "roles/pubsub.publisher",             # publish to topics
    "roles/cloudsql.client",              # Cloud SQL
    "roles/secretmanager.secretAccessor", # Secret Manager
    "roles/aiplatform.user",              # Vertex AI embeddings
  ]

  approval_worker_roles = [
    "roles/datastore.user",      # Firestore
    "roles/pubsub.subscriber",   # subscribe to topics
    "roles/pubsub.publisher",    # publish to triage-approved
    "roles/cloudsql.client",     # Cloud SQL
    "roles/bigquery.dataEditor", # BigQuery audit writes
  ]
}

resource "google_project_iam_member" "orchestrator_bindings" {
  for_each = toset(local.orchestrator_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}

resource "google_project_iam_member" "approval_worker_bindings" {
  for_each = toset(local.approval_worker_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.approval_worker_sa.email}"
}
