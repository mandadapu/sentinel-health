locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

resource "google_cloud_run_v2_job" "db_migrate" {
  name     = "${local.name_prefix}-db-migrate"
  location = var.region
  project  = var.project_id
  labels   = local.labels

  template {
    task_count  = 1
    parallelism = 1

    template {
      service_account = var.orchestrator_sa_email
      timeout         = "300s"
      max_retries     = 1

      vpc_access {
        connector = var.vpc_connector_id
        egress    = "ALL_TRAFFIC"
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.cloudsql_instance_connection]
        }
      }

      containers {
        name  = "migrate"
        image = var.orchestrator_image

        command = ["alembic", "upgrade", "head"]

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name  = "ENV"
          value = var.env
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "CLOUDSQL_INSTANCE"
          value = var.cloudsql_instance_connection
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }
}
