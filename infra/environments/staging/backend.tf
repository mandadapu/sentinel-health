terraform {
  backend "gcs" {
    bucket = "sentinel-health-tfstate-staging"
    prefix = "terraform/state"
  }
}
