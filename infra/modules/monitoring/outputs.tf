output "notification_channel_id" {
  description = "Email notification channel ID"
  value       = google_monitoring_notification_channel.email.id
}

output "alert_policy_ids" {
  description = "Map of alert policy names to their IDs"
  value = {
    dlq_depth            = google_monitoring_alert_policy.dlq_depth.id
    cloud_run_error_rate = google_monitoring_alert_policy.cloud_run_error_rate.id
    cloud_run_latency    = google_monitoring_alert_policy.cloud_run_latency.id
    cloudsql_connections = google_monitoring_alert_policy.cloudsql_connections.id
    cloudsql_cpu         = google_monitoring_alert_policy.cloudsql_cpu.id
  }
}

output "dashboard_id" {
  description = "Monitoring dashboard ID"
  value       = google_monitoring_dashboard.main.id
}
