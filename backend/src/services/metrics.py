"""Cloud Monitoring custom metrics for LLM usage tracking."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency in test/local dev
_client = None
_project_path: str = ""


def _get_client() -> Any:
    global _client  # noqa: PLW0603
    if _client is None:
        try:
            from google.cloud import monitoring_v3

            _client = monitoring_v3.MetricServiceClient()
        except Exception:
            logger.debug("Cloud Monitoring client not available — metrics disabled")
    return _client


def init_metrics(project_id: str) -> None:
    """Initialize the metrics subsystem with the GCP project ID."""
    global _project_path  # noqa: PLW0603
    _project_path = f"projects/{project_id}"


def record_llm_usage(
    model: str,
    node_name: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    """Record LLM usage metrics to Cloud Monitoring.

    Fire-and-forget: logs and swallows errors so callers are never blocked.
    """
    client = _get_client()
    if client is None or not _project_path:
        return

    try:
        from google.api import metric_pb2, monitored_resource_pb2
        from google.cloud.monitoring_v3 import CreateTimeSeriesRequest, TimeSeries, TimeInterval, TypedValue, Point

        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 1e9)
        interval = TimeInterval(
            end_time={"seconds": seconds, "nanos": nanos},
        )

        resource = monitored_resource_pb2.MonitoredResource(
            type="global",
            labels={"project_id": _project_path.split("/")[-1]},
        )

        series: list[TimeSeries] = []

        # Token counts (input + output as separate series)
        for token_type, count in [("input", input_tokens), ("output", output_tokens)]:
            series.append(
                TimeSeries(
                    metric=metric_pb2.Metric(
                        type="custom.googleapis.com/sentinel/llm/token_count",
                        labels={"model": model, "node": node_name, "token_type": token_type},
                    ),
                    resource=resource,
                    points=[Point(interval=interval, value=TypedValue(int64_value=count))],
                )
            )

        # Cost
        series.append(
            TimeSeries(
                metric=metric_pb2.Metric(
                    type="custom.googleapis.com/sentinel/llm/cost_usd",
                    labels={"model": model},
                ),
                resource=resource,
                points=[Point(interval=interval, value=TypedValue(double_value=cost_usd))],
            )
        )

        # Request count
        series.append(
            TimeSeries(
                metric=metric_pb2.Metric(
                    type="custom.googleapis.com/sentinel/llm/request_count",
                    labels={"model": model, "node": node_name},
                ),
                resource=resource,
                points=[Point(interval=interval, value=TypedValue(int64_value=1))],
            )
        )

        client.create_time_series(
            request=CreateTimeSeriesRequest(name=_project_path, time_series=series)
        )
    except Exception:
        logger.debug("Failed to write LLM metrics", exc_info=True)
