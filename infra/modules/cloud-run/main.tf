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
      min_instance_count = var.orchestrator_min_instances
      max_instance_count = var.orchestrator_max_instances
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

      env {
        name  = "EMBEDDING_MODEL"
        value = "voyage-3"
      }

      env {
        name  = "EMBEDDING_DIMENSION"
        value = "1024"
      }

      env {
        name  = "EMBEDDING_FALLBACK_MODEL"
        value = "text-embedding-004"
      }

      env {
        name  = "DEFAULT_CLASSIFIER_MODEL"
        value = var.classifier_model
      }

      env {
        name  = "SENTINEL_MODEL"
        value = var.sentinel_model
      }

      env {
        name  = "HALLUCINATION_THRESHOLD"
        value = var.hallucination_threshold
      }

      env {
        name  = "CONFIDENCE_THRESHOLD"
        value = var.confidence_threshold
      }

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        value = var.cors_allowed_origins
      }

      env {
        name = "VOYAGE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "voyage-api-key"
            version = "latest"
          }
        }
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
      min_instance_count = var.worker_min_instances
      max_instance_count = var.worker_max_instances
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

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        value = var.cors_allowed_origins
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

# Audit Consumer — single container, Pub/Sub triggered
resource "google_cloud_run_v2_service" "audit_consumer" {
  name     = "${local.name_prefix}-audit-consumer"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.audit_consumer_sa_email
    timeout         = "60s"

    scaling {
      min_instance_count = var.worker_min_instances
      max_instance_count = var.worker_max_instances
    }

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      name  = "audit-consumer"
      image = var.audit_consumer_image

      ports {
        container_port = 8080
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

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
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

# Frontend — nginx serving React SPA
resource "google_cloud_run_v2_service" "frontend" {
  name     = "${local.name_prefix}-frontend"
  location = var.region
  project  = var.project_id

  template {
    scaling {
      min_instance_count = var.worker_min_instances
      max_instance_count = var.worker_max_instances
    }

    containers {
      name  = "frontend"
      image = var.frontend_image

      ports {
        container_port = 3000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/"
          port = 3000
        }
        initial_delay_seconds = 3
        period_seconds        = 5
        failure_threshold     = 3
      }
    }
  }

  labels = local.labels
}

# Grant Pub/Sub service agent permission to invoke workers
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_cloud_run_v2_service_iam_member" "pubsub_invoker_approval_worker" {
  name     = google_cloud_run_v2_service.approval_worker.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_cloud_run_v2_service_iam_member" "pubsub_invoker_audit_consumer" {
  name     = google_cloud_run_v2_service.audit_consumer.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Allow unauthenticated access to orchestrator (fronted by load balancer in prod)
resource "google_cloud_run_v2_service_iam_member" "orchestrator_invoker" {
  name     = google_cloud_run_v2_service.orchestrator.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Allow unauthenticated access to frontend
resource "google_cloud_run_v2_service_iam_member" "frontend_invoker" {
  name     = google_cloud_run_v2_service.frontend.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}
