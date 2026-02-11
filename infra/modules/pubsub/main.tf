locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }

  topics = toset([
    "triage-completed",
    "audit-events",
    "triage-approved",
  ])

  # Push config per topic — only triage-completed and audit-events get push
  push_configs = {
    "triage-completed" = {
      push_endpoint       = "${var.approval_worker_url}/push/triage-completed"
      oidc_token_sa       = var.approval_worker_sa_email
      oidc_token_audience = var.approval_worker_url
    }
    "audit-events" = {
      push_endpoint       = "${var.audit_consumer_url}/push/audit-event"
      oidc_token_sa       = var.audit_consumer_sa_email
      oidc_token_audience = var.audit_consumer_url
    }
  }
}

# Main topics
resource "google_pubsub_topic" "main" {
  for_each = local.topics

  name    = "${local.name_prefix}-${each.value}"
  project = var.project_id
  labels  = local.labels

  message_retention_duration = "604800s" # 7 days
}

# Dead letter topics
resource "google_pubsub_topic" "dlq" {
  for_each = local.topics

  name    = "${local.name_prefix}-${each.value}-dlq"
  project = var.project_id
  labels  = local.labels
}

# Subscriptions with dead letter policy
resource "google_pubsub_subscription" "main" {
  for_each = local.topics

  name    = "${local.name_prefix}-${each.value}-sub"
  topic   = google_pubsub_topic.main[each.value].id
  project = var.project_id
  labels  = local.labels

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s" # 7 days
  retain_acked_messages      = true

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq[each.value].id
    max_delivery_attempts = 5
  }

  expiration_policy {
    ttl = "" # Never expire
  }

  # Push config with OIDC auth — only for topics that have a consumer
  dynamic "push_config" {
    for_each = contains(keys(local.push_configs), each.value) ? [local.push_configs[each.value]] : []

    content {
      push_endpoint = push_config.value.push_endpoint

      oidc_token {
        service_account_email = push_config.value.oidc_token_sa
        audience              = push_config.value.oidc_token_audience
      }

      attributes = {
        x-goog-version = "v1"
      }
    }
  }
}

# DLQ subscriptions (for monitoring/manual processing)
resource "google_pubsub_subscription" "dlq" {
  for_each = local.topics

  name    = "${local.name_prefix}-${each.value}-dlq-sub"
  topic   = google_pubsub_topic.dlq[each.value].id
  project = var.project_id
  labels  = local.labels

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"
  retain_acked_messages      = true
}

# Grant Pub/Sub service agent permission to publish to DLQ topics
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  for_each = local.topics

  topic   = google_pubsub_topic.dlq[each.value].id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  project = var.project_id
}

# Grant subscriber permissions — approval worker on triage-completed + triage-approved
resource "google_pubsub_subscription_iam_member" "approval_worker_subscriber" {
  for_each = toset(["triage-completed", "triage-approved"])

  subscription = google_pubsub_subscription.main[each.value].id
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${var.approval_worker_sa_email}"
  project      = var.project_id
}

# Grant subscriber permissions — audit consumer on audit-events
resource "google_pubsub_subscription_iam_member" "audit_consumer_subscriber" {
  subscription = google_pubsub_subscription.main["audit-events"].id
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${var.audit_consumer_sa_email}"
  project      = var.project_id
}
