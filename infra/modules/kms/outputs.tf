output "keyring_id" {
  description = "The ID of the KMS key ring"
  value       = google_kms_key_ring.keyring.id
}

output "keyring_name" {
  description = "The name of the KMS key ring"
  value       = google_kms_key_ring.keyring.name
}

output "cloudsql_crypto_key_id" {
  description = "The ID of the Cloud SQL CMEK crypto key"
  value       = google_kms_crypto_key.cloudsql_cmek.id
}

output "cloudsql_crypto_key_name" {
  description = "The name of the Cloud SQL CMEK crypto key"
  value       = google_kms_crypto_key.cloudsql_cmek.name
}
