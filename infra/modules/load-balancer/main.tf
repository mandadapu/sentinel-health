locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

# ---------------------------------------------------------------------------
# Serverless NEGs — point to Cloud Run services
# ---------------------------------------------------------------------------

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "${local.name_prefix}-frontend-neg"
  project               = var.project_id
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = var.frontend_cloud_run_service_name
  }
}

resource "google_compute_region_network_endpoint_group" "api_neg" {
  name                  = "${local.name_prefix}-api-neg"
  project               = var.project_id
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = var.orchestrator_cloud_run_service_name
  }
}

# ---------------------------------------------------------------------------
# Backend services
# ---------------------------------------------------------------------------

resource "google_compute_backend_service" "frontend" {
  name                  = "${local.name_prefix}-frontend-backend"
  project               = var.project_id
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg.id
  }

  security_policy = var.security_policy_id != "" ? var.security_policy_id : null

  log_config {
    enable = true
  }
}

resource "google_compute_backend_service" "api" {
  name                  = "${local.name_prefix}-api-backend"
  project               = var.project_id
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.api_neg.id
  }

  security_policy = var.security_policy_id != "" ? var.security_policy_id : null

  log_config {
    enable = true
  }
}

# ---------------------------------------------------------------------------
# URL map — route /api/* to backend, everything else to frontend
# ---------------------------------------------------------------------------

resource "google_compute_url_map" "default" {
  name            = "${local.name_prefix}-url-map"
  project         = var.project_id
  default_service = google_compute_backend_service.frontend.id

  host_rule {
    hosts        = [var.domain_name]
    path_matcher = "sentinel"
  }

  path_matcher {
    name            = "sentinel"
    default_service = google_compute_backend_service.frontend.id

    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.api.id
    }
  }
}

# ---------------------------------------------------------------------------
# Managed SSL certificate
# ---------------------------------------------------------------------------

resource "google_compute_managed_ssl_certificate" "default" {
  name    = "${local.name_prefix}-ssl-cert"
  project = var.project_id

  managed {
    domains = [var.domain_name]
  }
}

# ---------------------------------------------------------------------------
# HTTPS proxy + forwarding rule
# ---------------------------------------------------------------------------

resource "google_compute_target_https_proxy" "default" {
  name             = "${local.name_prefix}-https-proxy"
  project          = var.project_id
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

resource "google_compute_global_address" "lb_ip" {
  name    = "${local.name_prefix}-lb-ip"
  project = var.project_id
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "${local.name_prefix}-https-rule"
  project               = var.project_id
  target                = google_compute_target_https_proxy.default.id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip.address
}

# ---------------------------------------------------------------------------
# HTTP-to-HTTPS redirect
# ---------------------------------------------------------------------------

resource "google_compute_url_map" "http_redirect" {
  name    = "${local.name_prefix}-http-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_redirect" {
  name    = "${local.name_prefix}-http-redirect-proxy"
  project = var.project_id
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http_redirect" {
  name                  = "${local.name_prefix}-http-redirect-rule"
  project               = var.project_id
  target                = google_compute_target_http_proxy.http_redirect.id
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip.address
}
