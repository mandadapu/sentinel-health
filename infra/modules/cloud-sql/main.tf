locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

resource "google_sql_database_instance" "main" {
  name             = "${local.name_prefix}-postgres"
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_15"

  encryption_key_name = var.kms_crypto_key_id

  settings {
    tier              = var.tier
    availability_type = var.availability_type
    disk_size         = var.disk_size_gb
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = var.private_network_self_link
      allocated_ip_range                            = var.private_ip_range_name
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    user_labels = local.labels
  }

  deletion_protection = true

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_sql_database" "sentinel_health" {
  name     = "sentinel_health"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
}

resource "google_sql_user" "app_user" {
  name     = "sentinel_app"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
  password = "CHANGE_ME_VIA_SECRET_MANAGER"

  lifecycle {
    ignore_changes = [password]
  }
}
