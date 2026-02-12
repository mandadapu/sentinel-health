output "security_policy_id" {
  description = "Cloud Armor security policy ID"
  value       = google_compute_security_policy.sentinel.id
}

output "security_policy_self_link" {
  description = "Cloud Armor security policy self-link"
  value       = google_compute_security_policy.sentinel.self_link
}
