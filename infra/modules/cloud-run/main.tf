locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

# Orchestrator — multi-container (main + sidecar)
resource "google_cloud_run_v2_service" "orchestrator" {
  name     = "${local.name_prefix}-orchestrator"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.orchestrator_sa_email
    timeout         = "300s"

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

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

    # Main container — FastAPI orchestrator
    containers {
      name  = "orchestrator"
      image = var.orchestrator_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
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
        name  = "SIDECAR_URL"
        value = "http://localhost:8081"
      }

      env {
        name  = "CLOUDSQL_INSTANCE"
        value = var.cloudsql_instance_connection
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds = 30
      }
    }

    # Sidecar container — validator
    containers {
      name  = "validator-sidecar"
      image = var.sidecar_image

      ports {
        container_port = 8081
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "ENV"
        value = var.env
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8081
        }
        initial_delay_seconds = 3
        period_seconds        = 5
        failure_threshold     = 3
      }
    }
  }

  labels = local.labels
}

# Approval Worker — single container, Pub/Sub triggered
resource "google_cloud_run_v2_service" "approval_worker" {
  name     = "${local.name_prefix}-approval-worker"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.approval_worker_sa_email
    timeout         = "60s"

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

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
      name  = "approval-worker"
      image = var.approval_worker_image

      ports {
        container_port = 8080
      }

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

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }
    }
  }

  labels = local.labels
}

# Allow unauthenticated access to orchestrator (fronted by load balancer in prod)
resource "google_cloud_run_v2_service_iam_member" "orchestrator_invoker" {
  name     = google_cloud_run_v2_service.orchestrator.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}
