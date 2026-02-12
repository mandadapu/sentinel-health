locals {
  name_prefix = "sentinel-${var.env}"
  labels = {
    project     = "sentinel-health"
    environment = var.env
    managed_by  = "terraform"
    compliance  = "hipaa"
  }
}

# Cloud Armor security policy
resource "google_compute_security_policy" "sentinel" {
  name    = "${local.name_prefix}-security-policy"
  project = var.project_id

  # Default rule: allow
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }

  # Rate limiting rule
  rule {
    action   = "rate_based_ban"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      rate_limit_threshold {
        count        = var.rate_limit_requests_per_interval
        interval_sec = var.rate_limit_interval_sec
      }
      conform_action   = "allow"
      exceed_action    = "deny(429)"
      ban_duration_sec = 60
    }
    description = "Rate limit: ${var.rate_limit_requests_per_interval} requests per ${var.rate_limit_interval_sec}s"
  }

  # Block known malicious user agents
  rule {
    action   = "deny(403)"
    priority = "900"
    match {
      expr {
        expression = "request.headers['user-agent'].matches('(?i)(sqlmap|nikto|nmap|masscan|dirbuster)')"
      }
    }
    description = "Block known malicious user agents"
  }

  # OWASP CRS: Block SQL injection and XSS
  rule {
    action   = "deny(403)"
    priority = "800"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable') || evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "OWASP CRS: Block SQL injection and XSS"
  }

  # Optional geo-restriction (US-only for HIPAA)
  dynamic "rule" {
    for_each = var.enable_geo_restriction ? [1] : []
    content {
      action   = "deny(403)"
      priority = "700"
      match {
        expr {
          expression = "!origin.region_code.matches('US')"
        }
      }
      description = "Geo-restriction: US only"
    }
  }
}
