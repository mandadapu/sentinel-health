output "lb_ip_address" {
  description = "External IP address of the load balancer"
  value       = google_compute_global_address.lb_ip.address
}

output "ssl_certificate_id" {
  description = "Managed SSL certificate ID"
  value       = google_compute_managed_ssl_certificate.default.id
}
