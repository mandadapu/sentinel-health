"""Locust load tests for Sentinel-Health.

Target: 500 encounters/day (~0.35 req/s sustained, burst to 5 req/s).
ADR-3 latency budget: < 5s per triage encounter.

Usage:
    # Headless (CI-friendly)
    locust -f locustfile.py --headless -u 10 -r 2 -t 5m --csv results

    # Web UI
    locust -f locustfile.py
"""

import json
import random
import uuid
from pathlib import Path

from locust import HttpUser, between, task

ENCOUNTERS = json.loads(
    Path(__file__).parent.joinpath("data/encounters.json").read_text()
)


class TriageUser(HttpUser):
    """Simulates clinicians submitting encounters for triage."""

    host = "http://localhost:8080"
    wait_time = between(1, 5)

    @task(10)
    def submit_triage(self):
        encounter = random.choice(ENCOUNTERS)
        self.client.post(
            "/api/triage",
            json={
                "encounter_text": encounter["encounter_text"],
                "patient_id": f"pat-{uuid.uuid4().hex[:8]}",
                "encounter_id": str(uuid.uuid4()),
            },
            name="/api/triage",
            timeout=10,
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")


class ApprovalUser(HttpUser):
    """Simulates clinicians reviewing and approving triages."""

    host = "http://localhost:8082"
    wait_time = between(2, 10)

    @task(5)
    def approve_triage(self):
        self.client.post(
            "/api/approve",
            json={
                "encounter_id": str(uuid.uuid4()),
                "status": random.choice(["approved", "rejected"]),
                "reviewer_id": f"dr-{random.choice(['smith', 'jones', 'patel', 'chen', 'garcia'])}",
                "notes": "Load test approval",
            },
            name="/api/approve",
            timeout=5,
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")


class SSEUser(HttpUser):
    """Simulates dashboard clients connected via SSE."""

    host = "http://localhost:8080"
    wait_time = between(30, 60)

    @task
    def stream_triage_results(self):
        with self.client.get(
            "/api/stream/triage-results",
            stream=True,
            name="/api/stream/triage-results",
            timeout=35,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        break
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
