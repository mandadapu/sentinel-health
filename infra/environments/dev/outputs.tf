# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------
output "vpc_name" {
  description = "VPC network name"
  value       = module.networking.vpc_name
}

output "vpc_connector_id" {
  description = "Serverless VPC connector ID"
  value       = module.networking.vpc_connector_id
}

# ---------------------------------------------------------------------------
# Cloud SQL
# ---------------------------------------------------------------------------
output "cloudsql_instance_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = module.cloud_sql.instance_connection_name
}

output "cloudsql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = module.cloud_sql.private_ip_address
}

# ---------------------------------------------------------------------------
# Cloud Run
# ---------------------------------------------------------------------------
output "orchestrator_url" {
  description = "Orchestrator Cloud Run service URL"
  value       = module.cloud_run.orchestrator_url
}

output "approval_worker_url" {
  description = "Approval Worker Cloud Run service URL"
  value       = module.cloud_run.approval_worker_url
}

output "audit_consumer_url" {
  description = "Audit Consumer Cloud Run service URL"
  value       = module.cloud_run.audit_consumer_url
}

output "frontend_url" {
  description = "Frontend Cloud Run service URL"
  value       = module.cloud_run.frontend_url
}

# ---------------------------------------------------------------------------
# Migration Job
# ---------------------------------------------------------------------------
output "migration_job_name" {
  description = "Database migration Cloud Run Job name"
  value       = module.migration_job.job_name
}

# ---------------------------------------------------------------------------
# Pub/Sub
# ---------------------------------------------------------------------------
output "pubsub_topic_ids" {
  description = "Pub/Sub topic IDs"
  value       = module.pubsub.topic_ids
}

# ---------------------------------------------------------------------------
# BigQuery
# ---------------------------------------------------------------------------
output "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  value       = module.bigquery.dataset_id
}

# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
output "secret_ids" {
  description = "Secret Manager secret IDs"
  value       = module.secrets.secret_ids
}

# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------
output "monitoring_dashboard_id" {
  description = "Cloud Monitoring dashboard ID"
  value       = module.monitoring.dashboard_id
}

# ---------------------------------------------------------------------------
# Load Balancer
# ---------------------------------------------------------------------------
output "load_balancer_ip" {
  description = "Global load balancer IP address"
  value       = module.load_balancer.lb_ip_address
}
