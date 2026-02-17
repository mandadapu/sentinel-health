locals {
  name_prefix = "sentinel-${var.env}"

  # Services that handle PHI and must be inside the perimeter
  restricted_services = [
    "bigquery.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
  ]
}

resource "google_access_context_manager_service_perimeter" "sentinel" {
  parent = "accessPolicies/${var.access_policy_id}"
  name   = "accessPolicies/${var.access_policy_id}/servicePerimeters/${local.name_prefix}_perimeter"
  title  = "${local.name_prefix}-perimeter"

  status {
    resources = [
      "projects/${var.project_number}",
    ]

    restricted_services = local.restricted_services

    # Allow Cloud Run services within the project to access restricted APIs
    ingress_policies {
      ingress_from {
        identity_type = "ANY_IDENTITY"
        sources {
          resource = "projects/${var.project_number}"
        }
      }
      ingress_to {
        resources = ["projects/${var.project_number}"]
        operations {
          service_name = "*"
        }
      }
    }

    # Allow egress to Anthropic API (Claude) and Vertex AI for LLM inference
    egress_policies {
      egress_from {
        identity_type = "ANY_IDENTITY"
      }
      egress_to {
        resources = ["*"]
        operations {
          service_name = "aiplatform.googleapis.com"
        }
      }
    }
  }
}
