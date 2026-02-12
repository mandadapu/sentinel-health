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
# Notification channel — email
# ---------------------------------------------------------------------------
resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "${local.name_prefix}-alerts"
  type         = "email"

  labels = {
    email_address = var.notification_email
  }
}

# ---------------------------------------------------------------------------
# Alert: DLQ depth > 0 (any DLQ subscription has undelivered messages)
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "dlq_depth" {
  project      = var.project_id
  display_name = "${local.name_prefix} DLQ Depth"
  combiner     = "OR"

  conditions {
    display_name = "DLQ has undelivered messages"

    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND metric.type = \"pubsub.googleapis.com/subscription/num_undelivered_messages\" AND resource.label.subscription_id = monitoring.regex.full_match(\"${local.name_prefix}-.*-dlq-sub\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "DLQ messages detected. Follow the DLQ investigation runbook: docs/runbooks/dlq-investigation.md\n\nHIPAA requires investigation within 24 hours."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# Alert: Cloud Run error rate > 5%
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "cloud_run_error_rate" {
  project      = var.project_id
  display_name = "${local.name_prefix} Cloud Run Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error rate exceeds 5%"

    condition_monitoring_query_language {
      query = <<-MQL
        fetch cloud_run_revision
        | metric 'run.googleapis.com/request_count'
        | filter resource.service_name =~ '${local.name_prefix}-.*'
        | align rate(1m)
        | group_by [resource.service_name], [total: sum(val())]
        | {
            filter metric.response_code_class != '2xx'
            | group_by [resource.service_name], [errors: sum(val())]
          ;
            ident
          }
        | join
        | value [error_rate: val(0) / val(1) * 100]
        | condition error_rate > 5
      MQL

      duration = "120s"

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "Cloud Run service error rate exceeds 5%. Check Cloud Run logs for failing requests and recent deployments."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# Alert: Orchestrator p99 latency > 5000ms
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "cloud_run_latency" {
  project      = var.project_id
  display_name = "${local.name_prefix} Orchestrator Latency"
  combiner     = "OR"

  conditions {
    display_name = "Orchestrator p99 latency exceeds 5s"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\" AND resource.label.service_name = \"${var.cloud_run_service_names["orchestrator"]}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 5000
      duration        = "300s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_99"
        cross_series_reducer = "REDUCE_MAX"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "Orchestrator p99 latency exceeds 5 seconds. Check for slow LLM calls, database bottlenecks, or sidecar timeouts."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# Alert: Cloud SQL active connections drop to 0
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "cloudsql_connections" {
  project      = var.project_id
  display_name = "${local.name_prefix} Cloud SQL Connections"
  combiner     = "OR"

  conditions {
    display_name = "Cloud SQL connections dropped to zero"

    condition_threshold {
      filter          = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/postgresql/num_backends\" AND metadata.system_labels.name = monitoring.regex.full_match(\"${local.name_prefix}-.*\")"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "60s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MIN"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "Cloud SQL has zero active connections. Verify Cloud SQL instance is running and Cloud Run services can connect via VPC."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# Alert: Cloud SQL CPU utilization > 80%
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "cloudsql_cpu" {
  project      = var.project_id
  display_name = "${local.name_prefix} Cloud SQL CPU"
  combiner     = "OR"

  conditions {
    display_name = "Cloud SQL CPU exceeds 80%"

    condition_threshold {
      filter          = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/cpu/utilization\" AND metadata.system_labels.name = monitoring.regex.full_match(\"${local.name_prefix}-.*\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "600s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "Cloud SQL CPU utilization exceeds 80% for 10 minutes. Consider scaling up the instance tier or optimizing slow queries."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# Custom metrics — LLM usage tracking
# ---------------------------------------------------------------------------
resource "google_monitoring_metric_descriptor" "llm_token_count" {
  project      = var.project_id
  type         = "custom.googleapis.com/sentinel/llm/token_count"
  metric_kind  = "CUMULATIVE"
  value_type   = "INT64"
  display_name = "LLM Token Count"
  description  = "Total tokens consumed by LLM calls"

  labels {
    key         = "model"
    value_type  = "STRING"
    description = "LLM model identifier"
  }

  labels {
    key         = "node"
    value_type  = "STRING"
    description = "Pipeline node name"
  }

  labels {
    key         = "token_type"
    value_type  = "STRING"
    description = "input or output"
  }
}

resource "google_monitoring_metric_descriptor" "llm_cost_usd" {
  project      = var.project_id
  type         = "custom.googleapis.com/sentinel/llm/cost_usd"
  metric_kind  = "CUMULATIVE"
  value_type   = "DOUBLE"
  display_name = "LLM Cost USD"
  description  = "Cost in USD of LLM API calls"

  labels {
    key         = "model"
    value_type  = "STRING"
    description = "LLM model identifier"
  }
}

resource "google_monitoring_metric_descriptor" "llm_request_count" {
  project      = var.project_id
  type         = "custom.googleapis.com/sentinel/llm/request_count"
  metric_kind  = "CUMULATIVE"
  value_type   = "INT64"
  display_name = "LLM Request Count"
  description  = "Number of LLM API requests"

  labels {
    key         = "model"
    value_type  = "STRING"
    description = "LLM model identifier"
  }

  labels {
    key         = "node"
    value_type  = "STRING"
    description = "Pipeline node name"
  }
}

# ---------------------------------------------------------------------------
# Alert: LLM daily cost exceeds threshold
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "llm_daily_cost" {
  project      = var.project_id
  display_name = "${local.name_prefix} LLM Daily Cost"
  combiner     = "OR"

  conditions {
    display_name = "LLM daily cost exceeds threshold"

    condition_threshold {
      filter          = "metric.type = \"custom.googleapis.com/sentinel/llm/cost_usd\""
      comparison      = "COMPARISON_GT"
      threshold_value = var.llm_daily_cost_threshold
      duration        = "0s"

      aggregations {
        alignment_period     = "86400s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "LLM costs exceeded daily threshold of $${var.llm_daily_cost_threshold}. Check model routing distribution and token counts."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "86400s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# SLO — Orchestrator service
# ---------------------------------------------------------------------------
resource "google_monitoring_custom_service" "orchestrator" {
  project      = var.project_id
  service_id   = "${local.name_prefix}-orchestrator"
  display_name = "${local.name_prefix} Orchestrator"
}

# SLO: 99.5% availability (30-day rolling window)
resource "google_monitoring_slo" "orchestrator_availability" {
  project      = var.project_id
  service      = google_monitoring_custom_service.orchestrator.service_id
  slo_id       = "${local.name_prefix}-availability"
  display_name = "Orchestrator Availability"
  goal         = 0.995

  rolling_period_days = 30

  request_based_sli {
    good_total_ratio {
      good_service_filter  = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND resource.label.service_name = \"${var.cloud_run_service_names["orchestrator"]}\" AND metric.label.response_code_class = \"2xx\""
      total_service_filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND resource.label.service_name = \"${var.cloud_run_service_names["orchestrator"]}\""
    }
  }
}

# SLO: 95% of requests < 3s latency (30-day rolling window)
resource "google_monitoring_slo" "orchestrator_latency" {
  project      = var.project_id
  service      = google_monitoring_custom_service.orchestrator.service_id
  slo_id       = "${local.name_prefix}-latency"
  display_name = "Orchestrator Latency"
  goal         = 0.95

  rolling_period_days = 30

  request_based_sli {
    distribution_cut {
      distribution_filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\" AND resource.label.service_name = \"${var.cloud_run_service_names["orchestrator"]}\""

      range {
        max = 3000
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Alert: SLO burn-rate — availability
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "slo_burn_rate_availability" {
  project      = var.project_id
  display_name = "${local.name_prefix} SLO Burn Rate - Availability"
  combiner     = "AND"

  conditions {
    display_name = "Fast burn: 14.4x error budget consumption (1h)"

    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.orchestrator_availability.id}\", \"60m\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 14.4
      duration        = "0s"

      trigger {
        count = 1
      }
    }
  }

  conditions {
    display_name = "Slow burn: 6x error budget consumption (6h)"

    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.orchestrator_availability.id}\", \"360m\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 6
      duration        = "0s"

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "SLO availability burn rate alert. The orchestrator is consuming error budget faster than sustainable. Investigate failing requests immediately."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# Alert: SLO burn-rate — latency
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "slo_burn_rate_latency" {
  project      = var.project_id
  display_name = "${local.name_prefix} SLO Burn Rate - Latency"
  combiner     = "AND"

  conditions {
    display_name = "Fast burn: 14.4x latency budget consumption (1h)"

    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.orchestrator_latency.id}\", \"60m\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 14.4
      duration        = "0s"

      trigger {
        count = 1
      }
    }
  }

  conditions {
    display_name = "Slow burn: 6x latency budget consumption (6h)"

    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.orchestrator_latency.id}\", \"360m\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 6
      duration        = "0s"

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content   = "SLO latency burn rate alert. The orchestrator p95 latency is degrading faster than the budget allows. Check LLM response times and database performance."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  user_labels = local.labels
}

# ---------------------------------------------------------------------------
# Dashboard — operational overview
# ---------------------------------------------------------------------------
resource "google_monitoring_dashboard" "main" {
  project = var.project_id
  dashboard_json = jsonencode({
    displayName = "${local.name_prefix} Operations"
    gridLayout = {
      columns = 2
      widgets = [
        {
          title = "DLQ Depth by Subscription"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"pubsub_subscription\" AND metric.type = \"pubsub.googleapis.com/subscription/num_undelivered_messages\" AND resource.label.subscription_id = monitoring.regex.full_match(\"${local.name_prefix}-.*-dlq-sub\")"
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MAX"
                  }
                }
              }
              plotType = "LINE"
            }]
          }
        },
        {
          title = "Cloud Run Request Rate by Service"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND resource.label.service_name = monitoring.regex.full_match(\"${local.name_prefix}-.*\")"
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_RATE"
                    crossSeriesReducer = "REDUCE_SUM"
                    groupByFields      = ["resource.label.service_name"]
                  }
                }
              }
              plotType = "STACKED_BAR"
            }]
          }
        },
        {
          title = "Cloud Run Error Rate by Service"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.label.response_code_class != \"2xx\" AND resource.label.service_name = monitoring.regex.full_match(\"${local.name_prefix}-.*\")"
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_RATE"
                    crossSeriesReducer = "REDUCE_SUM"
                    groupByFields      = ["resource.label.service_name"]
                  }
                }
              }
              plotType = "LINE"
            }]
          }
        },
        {
          title = "Cloud Run p99 Latency by Service"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\" AND resource.label.service_name = monitoring.regex.full_match(\"${local.name_prefix}-.*\")"
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_PERCENTILE_99"
                    crossSeriesReducer = "REDUCE_MAX"
                    groupByFields      = ["resource.label.service_name"]
                  }
                }
              }
              plotType = "LINE"
            }]
          }
        },
        {
          title = "Cloud SQL Active Connections"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/postgresql/num_backends\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
              plotType = "LINE"
            }]
          }
        },
        {
          title = "Cloud SQL CPU Utilization"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/cpu/utilization\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
              plotType = "LINE"
            }]
          }
        },
        {
          title = "LLM Token Usage by Model"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type = \"custom.googleapis.com/sentinel/llm/token_count\""
                  aggregation = {
                    alignmentPeriod    = "3600s"
                    perSeriesAligner   = "ALIGN_DELTA"
                    crossSeriesReducer = "REDUCE_SUM"
                    groupByFields      = ["metric.label.model"]
                  }
                }
              }
              plotType = "STACKED_BAR"
            }]
          }
        },
        {
          title = "LLM Cost per Day (USD)"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type = \"custom.googleapis.com/sentinel/llm/cost_usd\""
                  aggregation = {
                    alignmentPeriod    = "86400s"
                    perSeriesAligner   = "ALIGN_DELTA"
                    crossSeriesReducer = "REDUCE_SUM"
                  }
                }
              }
              plotType = "LINE"
            }]
          }
        },
        {
          title = "LLM Requests by Model"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type = \"custom.googleapis.com/sentinel/llm/request_count\""
                  aggregation = {
                    alignmentPeriod    = "3600s"
                    perSeriesAligner   = "ALIGN_DELTA"
                    crossSeriesReducer = "REDUCE_SUM"
                    groupByFields      = ["metric.label.model"]
                  }
                }
              }
              plotType = "STACKED_BAR"
            }]
          }
        }
      ]
    }
  })
}
