output "job_name" {
  description = "Name of the database migration Cloud Run Job"
  value       = google_cloud_run_v2_job.db_migrate.name
}

output "job_id" {
  description = "ID of the database migration Cloud Run Job"
  value       = google_cloud_run_v2_job.db_migrate.id
}
