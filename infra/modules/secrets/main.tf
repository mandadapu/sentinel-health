locals {
  labels = {
    project    = "sentinel-health"
    managed_by = "terraform"
    compliance = "hipaa"
  }

  secrets = {
    "anthropic-api-key"     = { accessors = [var.orchestrator_sa_email] }
    "vertex-ai-api-key"     = { accessors = [var.orchestrator_sa_email] }
    "cloudsql-app-password" = { accessors = [var.orchestrator_sa_email, var.approval_worker_sa_email] }
  }
}

# Secret containers (values populated out-of-band via gcloud or CI)
resource "google_secret_manager_secret" "secrets" {
  for_each = local.secrets

  secret_id = each.key
  project   = var.project_id
  labels    = local.labels

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

# IAM: grant accessor role to service accounts
resource "google_secret_manager_secret_iam_member" "accessors" {
  for_each = merge([
    for secret_key, secret_config in local.secrets : {
      for sa_email in secret_config.accessors :
      "${secret_key}--${sa_email}" => {
        secret_id = secret_key
        sa_email  = sa_email
      }
    }
  ]...)

  secret_id = google_secret_manager_secret.secrets[each.value.secret_id].secret_id
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.sa_email}"
}
