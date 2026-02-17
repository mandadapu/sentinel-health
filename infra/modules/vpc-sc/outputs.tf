output "perimeter_name" {
  description = "VPC Service Controls perimeter name"
  value       = google_access_context_manager_service_perimeter.sentinel.name
}
