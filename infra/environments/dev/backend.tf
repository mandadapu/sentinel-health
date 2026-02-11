terraform {
  backend "gcs" {
    bucket = "sentinel-health-tfstate-dev"
    prefix = "terraform/state"
  }
}
