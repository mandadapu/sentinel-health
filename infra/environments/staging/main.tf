terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Enable required GCP APIs
# ---------------------------------------------------------------------------
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "bigquery.googleapis.com",
    "cloudkms.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
    "monitoring.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Networking — VPC, subnet, firewall, VPC connector, VPC peering
# ---------------------------------------------------------------------------
module "networking" {
  source = "../../modules/networking"

  project_id = var.project_id
  region     = var.region
  env        = var.env

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# KMS — Keyring + CMEK key for Cloud SQL
# ---------------------------------------------------------------------------
module "kms" {
  source = "../../modules/kms"

  project_id     = var.project_id
  region         = var.region
  env            = var.env
  project_number = var.project_number

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# IAM — Service accounts + least-privilege bindings
# ---------------------------------------------------------------------------
module "iam" {
  source = "../../modules/iam"

  project_id = var.project_id
  env        = var.env

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Cloud SQL — PostgreSQL 15 + pgvector, CMEK, private IP
# ---------------------------------------------------------------------------
module "cloud_sql" {
  source = "../../modules/cloud-sql"

  project_id                = var.project_id
  region                    = var.region
  env                       = var.env
  kms_crypto_key_id         = module.kms.cloudsql_crypto_key_id
  private_network_self_link = module.networking.vpc_self_link
  private_ip_range_name     = module.networking.private_ip_range_name

  depends_on = [module.kms, module.networking]
}

# ---------------------------------------------------------------------------
# Firestore — Native mode
# ---------------------------------------------------------------------------
module "firestore" {
  source = "../../modules/firestore"

  project_id = var.project_id
  region     = var.region
  env        = var.env

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Pub/Sub — 3 topics + DLQs
# ---------------------------------------------------------------------------
module "pubsub" {
  source = "../../modules/pubsub"

  project_id               = var.project_id
  env                      = var.env
  approval_worker_sa_email = module.iam.approval_worker_sa_email
  audit_consumer_sa_email  = module.iam.audit_consumer_sa_email
  approval_worker_url      = module.cloud_run.approval_worker_url
  audit_consumer_url       = module.cloud_run.audit_consumer_url

  depends_on = [module.iam, module.cloud_run]
}

# ---------------------------------------------------------------------------
# BigQuery — audit_trail table
# ---------------------------------------------------------------------------
module "bigquery" {
  source = "../../modules/bigquery"

  project_id = var.project_id
  region     = var.region
  env        = var.env

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Secrets — Secret Manager containers + IAM
# ---------------------------------------------------------------------------
module "secrets" {
  source = "../../modules/secrets"

  project_id               = var.project_id
  region                   = var.region
  orchestrator_sa_email    = module.iam.orchestrator_sa_email
  approval_worker_sa_email = module.iam.approval_worker_sa_email

  depends_on = [module.iam]
}

# ---------------------------------------------------------------------------
# Cloud Run — Orchestrator (multi-container) + Approval Worker
# ---------------------------------------------------------------------------
module "cloud_run" {
  source = "../../modules/cloud-run"

  project_id                   = var.project_id
  region                       = var.region
  env                          = var.env
  vpc_connector_id             = module.networking.vpc_connector_id
  orchestrator_sa_email        = module.iam.orchestrator_sa_email
  approval_worker_sa_email     = module.iam.approval_worker_sa_email
  audit_consumer_sa_email      = module.iam.audit_consumer_sa_email
  cloudsql_instance_connection = module.cloud_sql.instance_connection_name

  restrict_ingress = true

  depends_on = [
    module.networking,
    module.iam,
    module.cloud_sql,
    module.secrets,
  ]
}

# ---------------------------------------------------------------------------
# Cloud Armor — WAF + rate limiting
# ---------------------------------------------------------------------------
module "cloud_armor" {
  source = "../../modules/cloud-armor"

  project_id = var.project_id
  env        = var.env

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Load Balancer — Global HTTPS LB with Cloud Armor
# ---------------------------------------------------------------------------
module "load_balancer" {
  source = "../../modules/load-balancer"

  project_id                           = var.project_id
  region                               = var.region
  env                                  = var.env
  domain_name                          = var.domain_name
  frontend_cloud_run_service_name      = module.cloud_run.frontend_name
  orchestrator_cloud_run_service_name  = module.cloud_run.orchestrator_name
  security_policy_id                   = module.cloud_armor.security_policy_id

  depends_on = [module.cloud_run, module.cloud_armor]
}

# ---------------------------------------------------------------------------
# Migration Job — Cloud Run Job for Alembic migrations
# ---------------------------------------------------------------------------
module "migration_job" {
  source = "../../modules/migration-job"

  project_id                   = var.project_id
  region                       = var.region
  env                          = var.env
  orchestrator_sa_email        = module.iam.orchestrator_sa_email
  vpc_connector_id             = module.networking.vpc_connector_id
  cloudsql_instance_connection = module.cloud_sql.instance_connection_name

  depends_on = [module.networking, module.iam, module.cloud_sql]
}

# ---------------------------------------------------------------------------
# Monitoring — Alert policies + dashboard
# ---------------------------------------------------------------------------
module "monitoring" {
  source = "../../modules/monitoring"

  project_id         = var.project_id
  region             = var.region
  env                = var.env
  notification_email = var.notification_email

  cloud_run_service_names = {
    orchestrator    = module.cloud_run.orchestrator_name
    approval_worker = module.cloud_run.approval_worker_name
    audit_consumer  = module.cloud_run.audit_consumer_name
  }

  depends_on = [module.cloud_run, module.pubsub, module.cloud_sql]
}
