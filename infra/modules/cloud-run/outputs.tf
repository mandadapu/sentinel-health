output "orchestrator_url" {
  description = "URL of the orchestrator Cloud Run service"
  value       = google_cloud_run_v2_service.orchestrator.uri
}

output "orchestrator_name" {
  description = "Name of the orchestrator Cloud Run service"
  value       = google_cloud_run_v2_service.orchestrator.name
}

output "approval_worker_url" {
  description = "URL of the approval worker Cloud Run service"
  value       = google_cloud_run_v2_service.approval_worker.uri
}

output "approval_worker_name" {
  description = "Name of the approval worker Cloud Run service"
  value       = google_cloud_run_v2_service.approval_worker.name
}

output "audit_consumer_url" {
  description = "URL of the audit consumer Cloud Run service"
  value       = google_cloud_run_v2_service.audit_consumer.uri
}

output "audit_consumer_name" {
  description = "Name of the audit consumer Cloud Run service"
  value       = google_cloud_run_v2_service.audit_consumer.name
}

output "frontend_url" {
  description = "URL of the frontend Cloud Run service"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "frontend_name" {
  description = "Name of the frontend Cloud Run service"
  value       = google_cloud_run_v2_service.frontend.name
}
