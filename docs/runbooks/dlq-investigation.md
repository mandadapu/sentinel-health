# DLQ Investigation Runbook

HIPAA requires all dead-letter queue messages to be investigated within **24 hours** of arrival. This runbook covers triage, diagnosis, remediation, and documentation for every DLQ topic in the Sentinel-Health system.

---

## DLQ Topics

| DLQ Topic | Source Topic | Consumer | Push Endpoint |
|---|---|---|---|
| `sentinel-{env}-triage-completed-dlq` | `sentinel-{env}-triage-completed` | Approval Worker | `/push/triage-completed` |
| `sentinel-{env}-audit-events-dlq` | `sentinel-{env}-audit-events` | Audit Consumer | `/push/audit-event` |
| `sentinel-{env}-triage-approved-dlq` | `sentinel-{env}-triage-approved` | Approval Worker | (pull subscription) |

Messages land in a DLQ after **5 failed delivery attempts** (configured in Terraform `max_delivery_attempts = 5`). All DLQ subscriptions retain acknowledged messages for 7 days (`message_retention_duration = 604800s`).

---

## Severity Classification

| DLQ | Severity | Impact |
|---|---|---|
| `triage-completed-dlq` | **P1 — Critical** | Patient triage results are not reaching the approval queue. Clinicians cannot review or approve triage decisions. |
| `audit-events-dlq` | **P2 — High** | Audit trail has gaps in BigQuery. Firestore still holds real-time state, but compliance archive is incomplete. |
| `triage-approved-dlq` | **P3 — Medium** | Downstream approval notifications are failing. Approval itself is recorded in Firestore; this affects only post-approval workflows. |

---

## Step 1: Detection & Alerting

DLQ depth alerts should fire via Cloud Monitoring. If you are investigating proactively, check DLQ depth manually:

```bash
# Check unacknowledged message count on each DLQ subscription
gcloud pubsub subscriptions describe sentinel-${ENV}-triage-completed-dlq-sub \
  --project=sentinel-health-${ENV} \
  --format="value(messageRetentionDuration)"

# Pull a sample message (does not ack — use --auto-ack=false which is default)
gcloud pubsub subscriptions pull sentinel-${ENV}-triage-completed-dlq-sub \
  --project=sentinel-health-${ENV} \
  --limit=1 \
  --format=json
```

Check Cloud Monitoring metrics:

```
pubsub.googleapis.com/subscription/num_undelivered_messages
```

Filter by subscription names ending in `-dlq-sub`.

---

## Step 2: Pull and Inspect DLQ Messages

Pull messages without acknowledging them:

```bash
# Pull up to 10 messages for inspection
gcloud pubsub subscriptions pull sentinel-${ENV}-triage-completed-dlq-sub \
  --project=sentinel-health-${ENV} \
  --limit=10 \
  --format=json > /tmp/dlq-messages.json
```

For each message, decode the base64 payload:

```bash
echo '<base64-data-field>' | base64 --decode | jq .
```

Record the following for every message:
- `encounter_id`
- `patient_id` (encrypted reference)
- `timestamp` of the original event
- Pub/Sub `messageId` and `publishTime`
- Any Pub/Sub delivery attempt attributes

---

## Step 3: Diagnose Root Cause

### Common Failure Modes

#### 3a. Consumer Service Down or Unhealthy

```bash
# Check Cloud Run service status
gcloud run services describe sentinel-${ENV}-approval-worker \
  --region=us-central1 --project=sentinel-health-${ENV} \
  --format="value(status.conditions)"

gcloud run services describe sentinel-${ENV}-audit-consumer \
  --region=us-central1 --project=sentinel-health-${ENV} \
  --format="value(status.conditions)"

# Check health endpoint
curl -s https://<approval-worker-url>/health | jq .
curl -s https://<audit-consumer-url>/health | jq .
```

**Indicators:** 5xx responses in Cloud Run logs, container crash loops, OOM kills.

**Fix:** Check Cloud Run logs (`gcloud logging read`), fix the deployment issue, redeploy if needed.

#### 3b. Invalid Message Payload

The approval worker rejects messages with HTTP 400 if:
- Base64 decoding fails
- JSON parsing fails
- `encounter_id` is missing

The audit consumer rejects messages with HTTP 400 if:
- Base64 decoding or JSON parsing fails
- `encounter_id` is missing from the audit event

```bash
# Check Cloud Run logs for 400 responses
gcloud logging read \
  'resource.type="cloud_run_revision" AND
   resource.labels.service_name="sentinel-'${ENV}'-approval-worker" AND
   httpRequest.status=400' \
  --project=sentinel-health-${ENV} \
  --limit=20 \
  --format=json
```

**Indicators:** "Invalid message payload" or "Missing encounter_id" in logs.

**Fix:** Identify the upstream publisher producing malformed messages. Check the orchestrator's Pub/Sub publish code. These messages cannot be reprocessed — document the encounter IDs and manually reconcile (see Step 5).

#### 3c. Firestore / BigQuery Write Failure

```bash
# Check for Firestore errors in approval worker
gcloud logging read \
  'resource.type="cloud_run_revision" AND
   resource.labels.service_name="sentinel-'${ENV}'-approval-worker" AND
   severity>=ERROR' \
  --project=sentinel-health-${ENV} \
  --limit=20

# Check for BigQuery errors in audit consumer
gcloud logging read \
  'resource.type="cloud_run_revision" AND
   resource.labels.service_name="sentinel-'${ENV}'-audit-consumer" AND
   severity>=ERROR' \
  --project=sentinel-health-${ENV} \
  --limit=20
```

**Indicators:** Permission denied, quota exceeded, schema mismatch, deadline exceeded.

**Fix:** Resolve the downstream issue (IAM permissions, quota increase, schema migration), then replay messages (see Step 4).

#### 3d. OIDC Authentication Failure

Push subscriptions use OIDC tokens for authentication. If the service account is misconfigured, Pub/Sub cannot authenticate to the Cloud Run endpoint.

```bash
# Verify push subscription config
gcloud pubsub subscriptions describe sentinel-${ENV}-triage-completed-sub \
  --project=sentinel-health-${ENV} \
  --format="yaml(pushConfig)"
```

**Indicators:** Pub/Sub delivery logs show 401/403 responses.

**Fix:** Verify the OIDC service account email matches the consumer's Cloud Run invoker IAM binding. Reapply Terraform if needed (`make tf-plan && make tf-apply`).

#### 3e. Network / VPC Connectivity

```bash
# Check VPC connector status
gcloud compute networks vpc-access connectors describe sentinel-${ENV}-connector \
  --region=us-central1 --project=sentinel-health-${ENV}
```

**Indicators:** Connection timeouts, DNS resolution failures.

**Fix:** Verify VPC connector is active and Cloud Run services are configured to use it.

---

## Step 4: Replay DLQ Messages

Once the root cause is fixed, replay messages from the DLQ back to the original consumer.

### Option A: Republish to Original Topic

```bash
# Pull messages from DLQ, republish to source topic
gcloud pubsub subscriptions pull sentinel-${ENV}-triage-completed-dlq-sub \
  --project=sentinel-health-${ENV} \
  --limit=100 \
  --format=json \
  | jq -r '.[].message.data' \
  | while read -r data; do
      gcloud pubsub topics publish sentinel-${ENV}-triage-completed \
        --project=sentinel-health-${ENV} \
        --message="$(echo "$data" | base64 --decode)"
    done
```

### Option B: Direct API Call (Single Message)

For individual messages, call the consumer endpoint directly:

```bash
# Replay a single triage-completed message
curl -X POST https://<approval-worker-url>/push/triage-completed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{
    "message": {
      "data": "<base64-encoded-payload>",
      "messageId": "replayed-<original-messageId>",
      "publishTime": "<original-publishTime>"
    },
    "subscription": "sentinel-'${ENV}'-triage-completed-sub"
  }'
```

### After Replay

Verify the messages were processed:

```bash
# For triage-completed: check Firestore approval queue
# For audit-events: check BigQuery audit_trail table

# BigQuery verification
bq query --project_id=sentinel-health-${ENV} \
  "SELECT encounter_id, node_name, created_at
   FROM sentinel_health.audit_trail
   WHERE encounter_id IN ('<encounter_id_1>', '<encounter_id_2>')
   ORDER BY created_at"
```

Acknowledge the DLQ messages only after confirming successful reprocessing:

```bash
gcloud pubsub subscriptions ack sentinel-${ENV}-triage-completed-dlq-sub \
  --project=sentinel-health-${ENV} \
  --ack-ids=<ack-id-1>,<ack-id-2>
```

---

## Step 5: Manual Reconciliation

For messages that **cannot be replayed** (malformed payload, missing data):

1. Extract the `encounter_id` from the DLQ message
2. Look up the encounter in Firestore (source of truth for real-time state):

```bash
# Use the Firebase/Firestore console or:
gcloud firestore documents get \
  projects/sentinel-health-${ENV}/databases/(default)/documents/triage_sessions/<encounter_id>
```

3. If the encounter exists in Firestore but is missing from the approval queue, manually create the approval entry
4. If the encounter exists in Firestore but is missing from BigQuery, manually insert the audit row:

```bash
bq insert sentinel_health.audit_trail \
  --project_id=sentinel-health-${ENV} \
  /tmp/manual-audit-row.json
```

5. Document every manual reconciliation in the incident log (see Step 6)

---

## Step 6: HIPAA Incident Documentation

Every DLQ investigation **must** be documented, regardless of severity. Create an entry with:

| Field | Description |
|---|---|
| **Incident ID** | Auto-generated or manual (e.g., `DLQ-2026-0211-001`) |
| **Detection time** | When the alert fired or DLQ messages were discovered |
| **Investigation start** | When on-call began investigation |
| **DLQ topic** | Which DLQ topic was affected |
| **Message count** | Number of messages in the DLQ |
| **Affected encounters** | List of `encounter_id` values |
| **Root cause** | Category from Step 3 + detailed description |
| **PHI exposure risk** | Did any PHI leak outside the HIPAA perimeter? (Yes/No + details) |
| **Resolution** | What was done to fix the issue |
| **Messages replayed** | Count of successfully replayed messages |
| **Messages manually reconciled** | Count requiring manual intervention |
| **Resolution time** | When investigation was completed |
| **24-hour SLA met** | Yes/No — was the investigation completed within 24 hours of detection? |
| **Preventive action** | What changes prevent recurrence (code fix, alert tuning, capacity increase, etc.) |

Store incident reports in a designated compliance repository or document management system accessible to HIPAA auditors.

---

## Step 7: Post-Incident Verification

After resolution, confirm system health:

```bash
# 1. Verify no remaining DLQ messages
gcloud pubsub subscriptions pull sentinel-${ENV}-triage-completed-dlq-sub \
  --project=sentinel-health-${ENV} --limit=1
gcloud pubsub subscriptions pull sentinel-${ENV}-audit-events-dlq-sub \
  --project=sentinel-health-${ENV} --limit=1
gcloud pubsub subscriptions pull sentinel-${ENV}-triage-approved-dlq-sub \
  --project=sentinel-health-${ENV} --limit=1

# 2. Verify consumers are healthy
curl -s https://<approval-worker-url>/health | jq .
curl -s https://<audit-consumer-url>/health | jq .

# 3. Run daily reconciliation check
bq query --project_id=sentinel-health-${ENV} \
  "SELECT DATE(created_at) as day, COUNT(*) as events
   FROM sentinel_health.audit_trail
   WHERE created_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
   GROUP BY day
   ORDER BY day"

# 4. Confirm Cloud Monitoring alerts are cleared
gcloud monitoring policies list \
  --project=sentinel-health-${ENV} \
  --filter="displayName:dlq OR displayName:dead-letter"
```

---

## Escalation Path

| Timeframe | Action |
|---|---|
| **0–1 hour** | On-call engineer begins investigation |
| **1–4 hours** | If unresolved, escalate to platform team lead |
| **4–12 hours** | If unresolved, escalate to engineering manager + compliance officer |
| **12–24 hours** | If approaching SLA deadline, escalate to VP Engineering + HIPAA Privacy Officer |
| **>24 hours (SLA breach)** | Mandatory HIPAA incident report filed. Compliance officer assesses breach notification requirements per 45 CFR 164.400-414 |

---

## Quick Reference: gcloud Commands

```bash
# Set environment
export ENV=dev  # or staging, prod
export PROJECT=sentinel-health-${ENV}

# List all DLQ subscriptions
gcloud pubsub subscriptions list --project=$PROJECT \
  --filter="name:dlq" --format="table(name, topic)"

# Check undelivered message counts across all DLQ subs
for sub in triage-completed audit-events triage-approved; do
  echo "=== sentinel-${ENV}-${sub}-dlq-sub ==="
  gcloud monitoring time-series list $PROJECT \
    --filter="metric.type=pubsub.googleapis.com/subscription/num_undelivered_messages AND resource.labels.subscription_id=sentinel-${ENV}-${sub}-dlq-sub" \
    --interval-start-time=$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
    --format="table(points.value.int64Value)"
done

# Tail consumer logs in real-time
gcloud logging tail \
  'resource.type="cloud_run_revision" AND
   resource.labels.service_name=~"sentinel-'${ENV}'-(approval-worker|audit-consumer)"' \
  --project=$PROJECT
```
