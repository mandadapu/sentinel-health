terraform {
  backend "gcs" {
    bucket = "sentinel-health-tfstate-prod"
    prefix = "terraform/state"
  }
}
