locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

# -----------------------------------------------------------------------------
# VPC Network
# -----------------------------------------------------------------------------
resource "google_compute_network" "vpc" {
  name                    = "${local.name_prefix}-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
  description             = "Sentinel Health ${var.env} VPC network"
}

# -----------------------------------------------------------------------------
# Subnet
# -----------------------------------------------------------------------------
resource "google_compute_subnetwork" "subnet" {
  name                     = "${local.name_prefix}-subnet"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = "10.0.0.0/20"
  private_ip_google_access = true
  description              = "Sentinel Health ${var.env} primary subnet"
}

# -----------------------------------------------------------------------------
# Firewall — Deny all public ingress
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "deny_public_ingress" {
  name        = "${local.name_prefix}-deny-public-ingress"
  project     = var.project_id
  network     = google_compute_network.vpc.id
  description = "Deny all ingress from the public internet"
  direction   = "INGRESS"
  priority    = 1000

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}

# -----------------------------------------------------------------------------
# Firewall — Allow GCP health checks
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "allow_health_checks" {
  name        = "${local.name_prefix}-allow-health-checks"
  project     = var.project_id
  network     = google_compute_network.vpc.id
  description = "Allow TCP ingress from GCP health check ranges"
  direction   = "INGRESS"
  priority    = 900

  allow {
    protocol = "tcp"
  }

  source_ranges = [
    "130.211.0.0/22",
    "35.191.0.0/16",
  ]

  target_tags = ["allow-health-check"]
}

# -----------------------------------------------------------------------------
# Firewall — Allow internal traffic within the subnet CIDR
# -----------------------------------------------------------------------------
resource "google_compute_firewall" "allow_internal" {
  name        = "${local.name_prefix}-allow-internal"
  project     = var.project_id
  network     = google_compute_network.vpc.id
  description = "Allow all TCP, UDP, and ICMP traffic within the subnet CIDR"
  direction   = "INGRESS"
  priority    = 900

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/20"]
}

# -----------------------------------------------------------------------------
# Private IP range reserved for VPC peering (Cloud SQL)
# -----------------------------------------------------------------------------
resource "google_compute_global_address" "private_ip_range" {
  name          = "${local.name_prefix}-private-ip-range"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  description   = "Reserved private IP range for Cloud SQL VPC peering"

  labels = local.labels
}

# -----------------------------------------------------------------------------
# VPC Peering connection for Cloud SQL
# -----------------------------------------------------------------------------
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

# -----------------------------------------------------------------------------
# Serverless VPC Access Connector (Cloud Run -> VPC)
# -----------------------------------------------------------------------------
resource "google_vpc_access_connector" "connector" {
  name          = "${local.name_prefix}-connector"
  project       = var.project_id
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.id
  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 3
}
