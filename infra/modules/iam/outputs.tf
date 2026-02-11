output "orchestrator_sa_email" {
  description = "Email address of the orchestrator service account"
  value       = google_service_account.orchestrator_sa.email
}

output "orchestrator_sa_id" {
  description = "Fully-qualified ID of the orchestrator service account"
  value       = google_service_account.orchestrator_sa.id
}

output "approval_worker_sa_email" {
  description = "Email address of the approval worker service account"
  value       = google_service_account.approval_worker_sa.email
}

output "approval_worker_sa_id" {
  description = "Fully-qualified ID of the approval worker service account"
  value       = google_service_account.approval_worker_sa.id
}
