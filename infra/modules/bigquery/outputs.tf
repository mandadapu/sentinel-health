output "dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.sentinel_health.dataset_id
}

output "audit_trail_table_id" {
  description = "BigQuery audit trail table ID"
  value       = google_bigquery_table.audit_trail.table_id
}

output "dataset_self_link" {
  description = "BigQuery dataset self link"
  value       = google_bigquery_dataset.sentinel_health.self_link
}
