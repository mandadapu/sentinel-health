locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

# -------------------------------------------------------
# KMS Key Ring
# -------------------------------------------------------
resource "google_kms_key_ring" "keyring" {
  name     = "${local.name_prefix}-keyring"
  location = var.region
  project  = var.project_id
}

# -------------------------------------------------------
# Cloud SQL CMEK Key
# -------------------------------------------------------
resource "google_kms_crypto_key" "cloudsql_cmek" {
  name            = "cloudsql-cmek-key"
  key_ring        = google_kms_key_ring.keyring.id
  purpose         = "ENCRYPT_DECRYPT"
  rotation_period = "7776000s" # 90 days

  labels = local.labels

  lifecycle {
    prevent_destroy = true
  }
}

# -------------------------------------------------------
# Grant Cloud SQL Service Agent access to the CMEK key
# -------------------------------------------------------
resource "google_kms_crypto_key_iam_member" "cloudsql_sa_binding" {
  crypto_key_id = google_kms_crypto_key.cloudsql_cmek.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:service-${var.project_number}@gcp-sa-cloud-sql.iam.gserviceaccount.com"
}
