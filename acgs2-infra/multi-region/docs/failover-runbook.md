# ACGS2 Multi-Region Failover Runbook

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Last Updated** | 2026-01-03 |
| **Owner** | Platform Operations Team |
| **Review Cycle** | Quarterly |
| **Classification** | Internal - Operations |

---

## Table of Contents

1. [Overview](#overview)
2. [Failover Types](#failover-types)
3. [Pre-Failover Checklist](#pre-failover-checklist)
4. [Application Layer Failover](#application-layer-failover)
5. [Database Failover](#database-failover)
6. [Kafka Failover](#kafka-failover)
7. [Full Region Failover](#full-region-failover)
8. [Verification Procedures](#verification-procedures)
9. [Rollback Procedures](#rollback-procedures)
10. [Post-Failover Tasks](#post-failover-tasks)
11. [Communication Templates](#communication-templates)
12. [Troubleshooting](#troubleshooting)
13. [Emergency Contacts](#emergency-contacts)

---

## Overview

### Purpose

This runbook provides step-by-step procedures for executing manual failover operations in the ACGS2 multi-region deployment. It covers application, database, and messaging layer failovers, including verification and rollback procedures.

### Architecture Summary

```
                    ┌─────────────────────────────────────────────┐
                    │              Global Traffic                  │
                    │           (DNS / Load Balancer)              │
                    └──────────────────┬──────────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
            ▼                          ▼                          ▼
   ┌────────────────┐        ┌────────────────┐        ┌────────────────┐
   │  US-East-1     │◄──────►│  EU-West-1     │◄──────►│  AP-Southeast-1│
   │  (Primary)     │  Istio │  (Standby)     │  Istio │  (Standby)     │
   │                │  E-W   │                │  E-W   │                │
   │ ┌────────────┐ │        │ ┌────────────┐ │        │ ┌────────────┐ │
   │ │ claude-flow│ │        │ │ claude-flow│ │        │ │ claude-flow│ │
   │ └────────────┘ │        │ └────────────┘ │        │ └────────────┘ │
   │ ┌────────────┐ │        │ ┌────────────┐ │        │ ┌────────────┐ │
   │ │ neural-mcp │ │        │ │ neural-mcp │ │        │ │ neural-mcp │ │
   │ └────────────┘ │        │ └────────────┘ │        │ └────────────┘ │
   │ ┌────────────┐ │  WAL   │ ┌────────────┐ │  WAL   │ ┌────────────┐ │
   │ │ PostgreSQL │ │──────► │ │ PostgreSQL │ │──────► │ │ PostgreSQL │ │
   │ │  PRIMARY   │ │        │ │  STANDBY   │ │        │ │  STANDBY   │ │
   │ └────────────┘ │        │ └────────────┘ │        │ └────────────┘ │
   │ ┌────────────┐ │        │ ┌────────────┐ │        │ ┌────────────┐ │
   │ │   Kafka    │ │◄──────►│ │   Kafka    │ │◄──────►│ │   Kafka    │ │
   │ │ (MM2 Sync) │ │        │ │ (MM2 Sync) │ │        │ │ (MM2 Sync) │ │
   │ └────────────┘ │        │ └────────────┘ │        │ └────────────┘ │
   └────────────────┘        └────────────────┘        └────────────────┘
```

### Recovery Objectives

| Metric | Target | Measured |
|--------|--------|----------|
| **Application RTO** | < 60 seconds | Istio outlier detection |
| **Database RTO** | < 15 minutes | Manual promotion |
| **Database RPO** | < 1 minute | Async replication lag |
| **Kafka RTO** | < 5 minutes | MirrorMaker 2 |
| **Full Region RTO** | < 30 minutes | Complete failover |

### Key Terminology

| Term | Definition |
|------|------------|
| **RTO** | Recovery Time Objective - maximum acceptable downtime |
| **RPO** | Recovery Point Objective - maximum acceptable data loss |
| **Primary Region** | Region serving production traffic (currently us-east-1) |
| **Target Region** | Region receiving failover traffic |
| **WAL** | Write-Ahead Log - PostgreSQL replication mechanism |
| **E-W Gateway** | Istio East-West Gateway for cross-cluster communication |

---

## Failover Types

### 1. Automatic Application Failover (Istio-Managed)

- **Trigger**: Service health check failures
- **Mechanism**: Istio outlier detection + locality load balancing
- **RTO**: < 60 seconds
- **Operator Action**: None required (automatic)

### 2. Manual Database Failover

- **Trigger**: Primary PostgreSQL failure, region unavailable
- **Mechanism**: Standby promotion via `pg_ctl promote`
- **RTO**: < 15 minutes
- **Operator Action**: Required (this runbook)

### 3. Kafka Topic Failover

- **Trigger**: Primary Kafka cluster failure
- **Mechanism**: MirrorMaker 2 topic switching
- **RTO**: < 5 minutes
- **Operator Action**: Required (update consumer configs)

### 4. Full Region Failover

- **Trigger**: Complete region outage
- **Mechanism**: Combined database + Kafka + DNS failover
- **RTO**: < 30 minutes
- **Operator Action**: Required (this runbook)

---

## Pre-Failover Checklist

### Before Any Failover

Complete this checklist before initiating any failover:

```
[ ] 1. Confirm the issue requires failover
      - Is this a transient issue? (wait 5 minutes)
      - Can the issue be resolved without failover?
      - Has the on-call lead approved the failover?

[ ] 2. Verify target region health
      - All services running in target region
      - Database standby is streaming
      - Kafka MirrorMaker 2 is healthy

[ ] 3. Gather current state information
      - Note current primary region
      - Record current replication lag
      - Document active connections/sessions

[ ] 4. Notify stakeholders
      - Send initial communication (see templates below)
      - Update status page
      - Create incident ticket

[ ] 5. Prepare rollback plan
      - Verify rollback procedures are available
      - Confirm rollback team is on standby
```

### Environment Verification Commands

```bash
# Set context variables
export PRIMARY_CONTEXT="us-east-1"
export TARGET_CONTEXT="eu-west-1"

# 1. Verify Istio mesh health
istioctl proxy-status --context=${PRIMARY_CONTEXT}
istioctl proxy-status --context=${TARGET_CONTEXT}

# 2. Check cross-cluster service discovery
istioctl ps --context=${PRIMARY_CONTEXT} | grep -i ${TARGET_CONTEXT}

# 3. Verify PostgreSQL replication status
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  psql -U postgres -c "SELECT application_name, state, replay_lag FROM pg_stat_replication;"

# 4. Check MirrorMaker 2 connector status
kubectl exec -it deploy/mirrormaker2 -n kafka-system --context=${PRIMARY_CONTEXT} -- \
  curl -s http://localhost:8083/connectors/MirrorSourceConnector/status | jq '.connector.state'

# 5. Verify target region services
kubectl get pods -n acgs-services --context=${TARGET_CONTEXT} -o wide

# 6. Check application health endpoints
kubectl exec -it deploy/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} -- \
  curl -s http://localhost:8080/health
```

---

## Application Layer Failover

### Overview

Application failover is handled automatically by Istio's outlier detection and locality load balancing. This section covers manual intervention when automatic failover is insufficient.

### Automatic Failover (Default Behavior)

Istio DestinationRules are configured with:

```yaml
outlierDetection:
  consecutiveGatewayErrors: 3
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 100
```

**Expected automatic failover time**: ~55 seconds

### Manual Traffic Shift

Use when you need to proactively shift traffic away from a region:

#### Step 1: Update VirtualService Weights

```bash
# Option A: Complete shift to target region
cat <<EOF | kubectl apply --context=${PRIMARY_CONTEXT} -f -
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: claude-flow-traffic-shift
  namespace: claude-flow-system
spec:
  hosts:
    - claude-flow
  http:
    - route:
        - destination:
            host: claude-flow
            subset: ${TARGET_CONTEXT}
          weight: 100
        - destination:
            host: claude-flow
            subset: ${PRIMARY_CONTEXT}
          weight: 0
EOF
```

#### Step 2: Verify Traffic Shift

```bash
# Check Envoy cluster endpoints
kubectl exec -it deploy/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} -- \
  pilot-agent request GET clusters | grep -i "outbound"

# Monitor traffic distribution
kubectl logs -l istio=ingressgateway -n istio-system --context=${TARGET_CONTEXT} | \
  grep "claude-flow" | tail -20
```

#### Step 3: Scale Down Primary Region (Optional)

```bash
# Scale down to prevent split-brain scenarios
kubectl scale deployment claude-flow --replicas=0 \
  -n claude-flow-system --context=${PRIMARY_CONTEXT}

kubectl scale deployment neural-mcp --replicas=0 \
  -n neural-mcp-system --context=${PRIMARY_CONTEXT}
```

### Rollback Application Failover

```bash
# Restore traffic weights
cat <<EOF | kubectl apply --context=${PRIMARY_CONTEXT} -f -
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: claude-flow-traffic-shift
  namespace: claude-flow-system
spec:
  hosts:
    - claude-flow
  http:
    - route:
        - destination:
            host: claude-flow
            subset: ${PRIMARY_CONTEXT}
          weight: 80
        - destination:
            host: claude-flow
            subset: ${TARGET_CONTEXT}
          weight: 20
EOF

# Scale up primary region
kubectl scale deployment claude-flow --replicas=2 \
  -n claude-flow-system --context=${PRIMARY_CONTEXT}

kubectl scale deployment neural-mcp --replicas=2 \
  -n neural-mcp-system --context=${PRIMARY_CONTEXT}
```

---

## Database Failover

### Prerequisites

- Confirm standby is streaming and lag is acceptable
- Ensure no active long-running transactions on primary
- Verify target region has network connectivity

### Phase 1: Assess Situation

```bash
# Check replication status on primary
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  psql -U postgres -c "
    SELECT
      application_name,
      state,
      sync_state,
      replay_lag,
      pg_wal_lsn_diff(sent_lsn, replay_lsn) as lag_bytes
    FROM pg_stat_replication;
  "

# Check standby replication status
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "
    SELECT
      pg_is_in_recovery() as is_standby,
      pg_last_wal_receive_lsn() as last_received,
      pg_last_wal_replay_lsn() as last_replayed,
      pg_last_xact_replay_timestamp() as last_replay_time,
      now() - pg_last_xact_replay_timestamp() as replay_lag
    ;
  "
```

### Phase 2: Stop Traffic to Primary Database

```bash
# Stop application writes by scaling down services
kubectl scale deployment claude-flow --replicas=0 \
  -n claude-flow-system --context=${PRIMARY_CONTEXT}

kubectl scale deployment neural-mcp --replicas=0 \
  -n neural-mcp-system --context=${PRIMARY_CONTEXT}

# Wait for connections to drain (30 seconds)
sleep 30

# Verify no active connections
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  psql -U postgres -c "
    SELECT count(*) as active_connections
    FROM pg_stat_activity
    WHERE state = 'active' AND usename != 'postgres';
  "
```

### Phase 3: Promote Standby to Primary

#### Option A: Clean Promotion (Primary Accessible)

```bash
# On primary: Stop PostgreSQL cleanly
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  pg_ctl stop -D /bitnami/postgresql/data -m fast

# On standby: Verify final replication position
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"

# Promote standby to primary
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  pg_ctl promote -D /bitnami/postgresql/data

# Verify promotion
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_is_in_recovery();"
# Expected: f (false = no longer in recovery = now primary)
```

#### Option B: Emergency Promotion (Primary Inaccessible)

```bash
# IMPORTANT: Only use when primary is completely unavailable
# Data loss may occur equal to replication lag

# On standby: Check last known replication position
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "
    SELECT
      pg_last_wal_receive_lsn() as last_received,
      pg_last_xact_replay_timestamp() as last_transaction,
      now() - pg_last_xact_replay_timestamp() as potential_data_loss
    ;
  "

# DECISION POINT: Accept data loss and proceed?
# If replication lag > 1 minute, escalate to management before proceeding

# Promote standby (emergency)
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  pg_ctl promote -D /bitnami/postgresql/data

# Verify promotion
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_is_in_recovery();"
```

### Phase 4: Update Application Configuration

```bash
# Update database connection ConfigMaps to point to new primary
kubectl patch configmap claude-flow-config -n claude-flow-system \
  --context=${TARGET_CONTEXT} \
  -p '{"data":{"POSTGRESQL_HOST":"postgresql-standby.database.svc.cluster.local"}}'

kubectl patch configmap neural-mcp-config -n neural-mcp-system \
  --context=${TARGET_CONTEXT} \
  -p '{"data":{"POSTGRESQL_HOST":"postgresql-standby.database.svc.cluster.local"}}'

# Restart services to pick up new config
kubectl rollout restart deployment/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT}
kubectl rollout restart deployment/neural-mcp -n neural-mcp-system --context=${TARGET_CONTEXT}

# Wait for rollout
kubectl rollout status deployment/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} --timeout=5m
kubectl rollout status deployment/neural-mcp -n neural-mcp-system --context=${TARGET_CONTEXT} --timeout=5m
```

### Phase 5: Verify Database Failover

```bash
# Test write operations
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U acgs -d acgs -c "
    CREATE TABLE IF NOT EXISTS failover_test (
      id SERIAL PRIMARY KEY,
      created_at TIMESTAMP DEFAULT NOW()
    );
    INSERT INTO failover_test (created_at) VALUES (NOW());
    SELECT * FROM failover_test;
  "

# Verify application connectivity
kubectl exec -it deploy/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} -- \
  curl -s http://localhost:8080/health | jq '.database'

# Check connection pool
kubectl exec -it deploy/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} -- \
  curl -s http://localhost:8080/metrics | grep "db_connections"
```

### Phase 6: Set Up Reverse Replication (Post-Failover)

After the old primary is recovered, set it up as a standby:

```bash
# On old primary (now standby): Stop if running
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  pg_ctl stop -D /bitnami/postgresql/data -m fast || true

# Clear old data and reinitialize as standby
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- bash -c '
  rm -rf /bitnami/postgresql/data/*
  PGPASSWORD="${POSTGRESQL_REPLICATION_PASSWORD}" pg_basebackup \
    -h postgresql-standby.database.svc.${TARGET_CONTEXT}.local \
    -p 5432 \
    -U replication_user \
    -D /bitnami/postgresql/data \
    -Fp -Xs -P -R \
    --checkpoint=fast \
    --wal-method=stream
  touch /bitnami/postgresql/data/standby.signal
  chmod 700 /bitnami/postgresql/data
'

# Restart as standby
kubectl delete pod postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT}

# Verify new standby is streaming
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

---

## Kafka Failover

### Overview

Kafka MirrorMaker 2 provides bidirectional replication between regions. During failover, consumers need to be redirected to the surviving region's topics.

### Check MirrorMaker 2 Status

```bash
# Check connector status
kubectl exec -it deploy/mirrormaker2 -n kafka-system --context=${PRIMARY_CONTEXT} -- \
  curl -s http://localhost:8083/connectors | jq

# Check replication lag
kubectl exec -it deploy/mirrormaker2 -n kafka-system --context=${PRIMARY_CONTEXT} -- \
  curl -s http://localhost:8083/connectors/MirrorSourceConnector/status | jq

# Check Prometheus metrics
kubectl port-forward svc/mirrormaker2-metrics -n kafka-system 9404:9404 --context=${TARGET_CONTEXT} &
curl -s http://localhost:9404/metrics | grep kafka_mirrormaker
```

### Consumer Failover Procedure

#### Step 1: Identify Active Topics

```bash
# List topics in target region
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-topics.sh --bootstrap-server localhost:9093 --list | grep -E "^acgs\."

# List mirrored topics (from primary)
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-topics.sh --bootstrap-server localhost:9093 --list | grep -E "^${PRIMARY_CONTEXT}\."
```

#### Step 2: Update Consumer Configurations

Consumers need to switch from primary topics to either:
- Local topics (if the region generates its own events)
- Mirrored topics (prefixed with source region name)

```bash
# Update consumer group configs
kubectl patch configmap kafka-consumer-config -n acgs-services \
  --context=${TARGET_CONTEXT} \
  -p '{
    "data": {
      "KAFKA_TOPICS": "acgs.agent.messages,acgs.agent.events,acgs.audit.events",
      "KAFKA_FALLBACK_TOPICS": "'${PRIMARY_CONTEXT}'.acgs.agent.messages,'${PRIMARY_CONTEXT}'.acgs.agent.events"
    }
  }'

# Restart consumers
kubectl rollout restart deployment/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT}
kubectl rollout restart deployment/neural-mcp -n neural-mcp-system --context=${TARGET_CONTEXT}
```

#### Step 3: Reset Consumer Offsets (If Needed)

```bash
# Get current consumer group offsets
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9093 \
  --group acgs-agent-consumers --describe

# Reset to latest (skip old messages)
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9093 \
  --group acgs-agent-consumers \
  --reset-offsets --to-latest \
  --topic acgs.agent.messages \
  --execute

# OR reset to timestamp (recover from specific point)
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9093 \
  --group acgs-agent-consumers \
  --reset-offsets --to-datetime 2026-01-03T00:00:00.000 \
  --topic acgs.agent.messages \
  --execute
```

### Verify Kafka Failover

```bash
# Check consumer group lag
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9093 \
  --group acgs-agent-consumers --describe

# Produce test message
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  echo "test-failover-$(date +%s)" | kafka-console-producer.sh \
  --bootstrap-server localhost:9093 \
  --topic acgs.agent.messages

# Verify consumption
kubectl logs -l app.kubernetes.io/name=claude-flow -n claude-flow-system \
  --context=${TARGET_CONTEXT} --tail=20 | grep "test-failover"
```

---

## Full Region Failover

### Procedure Overview

A full region failover combines all individual failovers in sequence:

1. Application traffic shift
2. Database promotion
3. Kafka consumer reconfiguration
4. DNS/external access updates

### Execution Timeline

| Time | Action | Owner |
|------|--------|-------|
| T+0:00 | Incident declared, failover initiated | On-Call Lead |
| T+0:02 | Pre-flight checks complete | Operations |
| T+0:05 | Application traffic shifted | Operations |
| T+0:10 | Database promoted | DBA |
| T+0:15 | Kafka consumers reconfigured | Operations |
| T+0:20 | Verification complete | Operations |
| T+0:25 | DNS updated (if applicable) | Network |
| T+0:30 | Failover complete | On-Call Lead |

### Step-by-Step Execution

#### Step 1: Initialize Failover

```bash
# Set environment
export INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
export PRIMARY_CONTEXT="us-east-1"
export TARGET_CONTEXT="eu-west-1"
export LOG_FILE="/tmp/failover-${INCIDENT_ID}.log"

# Create log file
echo "Failover initiated: $(date)" | tee -a $LOG_FILE
echo "Incident: $INCIDENT_ID" | tee -a $LOG_FILE
echo "Primary: $PRIMARY_CONTEXT -> Target: $TARGET_CONTEXT" | tee -a $LOG_FILE
```

#### Step 2: Execute Application Failover

```bash
echo "=== Step 2: Application Failover ===" | tee -a $LOG_FILE

# Shift traffic
kubectl apply -f - --context=${PRIMARY_CONTEXT} <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: emergency-traffic-shift
  namespace: istio-system
spec:
  hosts:
    - "*.acgs.io"
  http:
    - route:
        - destination:
            host: istio-eastwestgateway.istio-system.svc.cluster.local
            port:
              number: 15443
          weight: 100
EOF

# Scale down primary services
kubectl scale deployment --all --replicas=0 -n claude-flow-system --context=${PRIMARY_CONTEXT}
kubectl scale deployment --all --replicas=0 -n neural-mcp-system --context=${PRIMARY_CONTEXT}

echo "Application failover complete: $(date)" | tee -a $LOG_FILE
```

#### Step 3: Execute Database Failover

```bash
echo "=== Step 3: Database Failover ===" | tee -a $LOG_FILE

# Record final replication position
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_last_wal_receive_lsn(), pg_last_xact_replay_timestamp();" | tee -a $LOG_FILE

# Promote standby
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  pg_ctl promote -D /bitnami/postgresql/data

# Wait for promotion
sleep 10

# Verify
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_is_in_recovery();" | tee -a $LOG_FILE

echo "Database failover complete: $(date)" | tee -a $LOG_FILE
```

#### Step 4: Execute Kafka Failover

```bash
echo "=== Step 4: Kafka Failover ===" | tee -a $LOG_FILE

# Update consumer configs
kubectl patch configmap kafka-consumer-config -n acgs-services \
  --context=${TARGET_CONTEXT} \
  -p '{"data":{"KAFKA_BOOTSTRAP_SERVERS":"kafka.kafka-system.svc.cluster.local:9093"}}'

# Restart services
kubectl rollout restart deployment -n claude-flow-system --context=${TARGET_CONTEXT}
kubectl rollout restart deployment -n neural-mcp-system --context=${TARGET_CONTEXT}

# Wait for rollouts
kubectl rollout status deployment/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} --timeout=5m
kubectl rollout status deployment/neural-mcp -n neural-mcp-system --context=${TARGET_CONTEXT} --timeout=5m

echo "Kafka failover complete: $(date)" | tee -a $LOG_FILE
```

#### Step 5: Update External DNS (If Applicable)

```bash
echo "=== Step 5: DNS Update ===" | tee -a $LOG_FILE

# If using external-dns or Route53
# aws route53 change-resource-record-sets --hosted-zone-id Z1234567890 \
#   --change-batch file://dns-failover.json

# For manual DNS update, provide instructions to network team:
echo "DNS Update Required:" | tee -a $LOG_FILE
echo "  - Update api.acgs.io to point to ${TARGET_CONTEXT} load balancer" | tee -a $LOG_FILE
echo "  - TTL: 60 seconds" | tee -a $LOG_FILE

echo "DNS update initiated: $(date)" | tee -a $LOG_FILE
```

#### Step 6: Final Verification

```bash
echo "=== Step 6: Verification ===" | tee -a $LOG_FILE

# Run comprehensive health checks
./acgs2-infra/multi-region/scripts/test-failover.sh \
  --service claude-flow \
  --dry-run \
  ${TARGET_CONTEXT} ${PRIMARY_CONTEXT} | tee -a $LOG_FILE

# Verify all services
kubectl get pods -A --context=${TARGET_CONTEXT} | grep -v Running | tee -a $LOG_FILE

echo "=== Failover Complete ===" | tee -a $LOG_FILE
echo "Completed at: $(date)" | tee -a $LOG_FILE
echo "Log file: $LOG_FILE"
```

---

## Verification Procedures

### Service Health Verification

```bash
# 1. Check all pods are running
kubectl get pods -A --context=${TARGET_CONTEXT} -o wide | grep -v "Running\|Completed"

# 2. Check Istio proxy status
istioctl proxy-status --context=${TARGET_CONTEXT}

# 3. Check service endpoints
kubectl get endpoints -n claude-flow-system --context=${TARGET_CONTEXT}
kubectl get endpoints -n neural-mcp-system --context=${TARGET_CONTEXT}

# 4. Test service-to-service communication
kubectl exec -it deploy/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} -- \
  curl -s http://neural-mcp.neural-mcp-system:8080/health

# 5. Check application logs for errors
kubectl logs -l app.kubernetes.io/name=claude-flow -n claude-flow-system \
  --context=${TARGET_CONTEXT} --tail=50 | grep -i error

kubectl logs -l app.kubernetes.io/name=neural-mcp -n neural-mcp-system \
  --context=${TARGET_CONTEXT} --tail=50 | grep -i error
```

### Database Health Verification

```bash
# 1. Verify PostgreSQL is primary (not in recovery)
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_is_in_recovery();"
# Expected: f (false)

# 2. Check connection count
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# 3. Test write operations
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U acgs -d acgs -c "INSERT INTO failover_test (created_at) VALUES (NOW()) RETURNING *;"

# 4. Check for any replication errors
kubectl logs postgresql-standby-0 -n database --context=${TARGET_CONTEXT} --tail=50 | grep -i error
```

### Kafka Health Verification

```bash
# 1. Check broker status
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-broker-api-versions.sh --bootstrap-server localhost:9093

# 2. Check topic health
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-topics.sh --bootstrap-server localhost:9093 --describe --topic acgs.agent.messages

# 3. Check consumer lag
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9093 \
  --group acgs-agent-consumers --describe

# 4. Test message flow
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- bash -c '
  echo "healthcheck-$(date +%s)" | kafka-console-producer.sh \
    --bootstrap-server localhost:9093 --topic acgs.agent.messages
'
```

### End-to-End Verification

```bash
# 1. Run the automated failover test script
./acgs2-infra/multi-region/scripts/test-failover.sh \
  --service claude-flow \
  --verbose \
  ${TARGET_CONTEXT} ${PRIMARY_CONTEXT}

# 2. Check Prometheus metrics
kubectl port-forward svc/prometheus -n monitoring 9090:9090 --context=${TARGET_CONTEXT} &
# Access http://localhost:9090 and query:
# - up{job="claude-flow"}
# - pg_replication_lag_seconds
# - kafka_consumer_lag

# 3. Check compliance verification (if applicable)
kubectl create job compliance-post-failover-$(date +%s) \
  --from=cronjob/compliance-verification \
  -n compliance --context=${TARGET_CONTEXT}

kubectl logs -l job-name=compliance-post-failover -n compliance --context=${TARGET_CONTEXT}
```

---

## Rollback Procedures

### When to Rollback

Consider rollback if:
- Target region experiences issues after failover
- Original region has recovered and is more stable
- Business requirement to return to original region

### Rollback Checklist

```
[ ] 1. Confirm rollback is necessary and approved
[ ] 2. Verify original region (now standby) is healthy
[ ] 3. Synchronize any data changes back to original region
[ ] 4. Notify stakeholders
[ ] 5. Execute rollback (reverse of failover)
[ ] 6. Verify rollback complete
```

### Application Rollback

```bash
# Reverse traffic weights
kubectl apply -f - --context=${PRIMARY_CONTEXT} <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: emergency-traffic-shift
  namespace: istio-system
spec:
  hosts:
    - "*.acgs.io"
  http:
    - route:
        - destination:
            host: claude-flow.claude-flow-system.svc.cluster.local
          weight: 100
EOF

# Scale up original region
kubectl scale deployment --all --replicas=2 -n claude-flow-system --context=${PRIMARY_CONTEXT}
kubectl scale deployment --all --replicas=2 -n neural-mcp-system --context=${PRIMARY_CONTEXT}

# Scale down failover region
kubectl scale deployment --all --replicas=0 -n claude-flow-system --context=${TARGET_CONTEXT}
kubectl scale deployment --all --replicas=0 -n neural-mcp-system --context=${TARGET_CONTEXT}
```

### Database Rollback

**WARNING**: Database rollback requires promoting the old primary (now standby) back to primary. This may result in data loss if the current primary has newer data.

```bash
# 1. Stop writes to current primary
kubectl scale deployment --all --replicas=0 -n claude-flow-system --context=${TARGET_CONTEXT}
kubectl scale deployment --all --replicas=0 -n neural-mcp-system --context=${TARGET_CONTEXT}

# 2. Wait for replication to catch up
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_last_wal_receive_lsn(), pg_last_xact_replay_timestamp();"

# 3. Stop current primary (was standby)
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  pg_ctl stop -D /bitnami/postgresql/data -m fast

# 4. Promote original primary (was standby)
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  pg_ctl promote -D /bitnami/postgresql/data

# 5. Reconfigure failover region as standby
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- bash -c '
  rm -rf /bitnami/postgresql/data/*
  PGPASSWORD="${POSTGRESQL_REPLICATION_PASSWORD}" pg_basebackup \
    -h postgresql-primary.database.svc.cluster.local \
    -p 5432 -U replication_user \
    -D /bitnami/postgresql/data \
    -Fp -Xs -P -R
  touch /bitnami/postgresql/data/standby.signal
'
```

---

## Post-Failover Tasks

### Immediate (Within 1 Hour)

```
[ ] 1. Update status page to "Operational"
[ ] 2. Send resolution communication
[ ] 3. Verify all monitoring is functional
[ ] 4. Check for any failed jobs/processes
[ ] 5. Verify compliance CronJobs passed
```

### Short-Term (Within 24 Hours)

```
[ ] 1. Complete incident report
[ ] 2. Set up reverse replication (old primary as standby)
[ ] 3. Update runbook if needed
[ ] 4. Review Prometheus/Grafana dashboards
[ ] 5. Verify backup schedules on new primary
```

### Long-Term (Within 1 Week)

```
[ ] 1. Conduct post-incident review
[ ] 2. Update capacity planning
[ ] 3. Schedule failback (if appropriate)
[ ] 4. Run tabletop exercise with team
[ ] 5. Update disaster recovery documentation
```

### Monitoring Verification

```bash
# Verify Prometheus scraping targets
kubectl port-forward svc/prometheus -n monitoring 9090:9090 --context=${TARGET_CONTEXT} &
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'

# Verify alerting rules loaded
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups | length'

# Check for any firing alerts
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts | map(select(.state == "firing"))'

# Verify Grafana dashboards
kubectl port-forward svc/grafana -n monitoring 3000:3000 --context=${TARGET_CONTEXT} &
# Access http://localhost:3000 and verify dashboards
```

---

## Communication Templates

### Initial Notification

```
Subject: [INCIDENT] ACGS2 Service Degradation - Failover Initiated

Severity: P1 - Critical
Status: Investigation In Progress
Start Time: [TIME] UTC

Summary:
We are experiencing service degradation in [PRIMARY_REGION]. A regional failover to [TARGET_REGION] has been initiated.

Impact:
- Brief service interruption (< 60 seconds) during failover
- Some database transactions may need to be retried
- Event processing may experience delays

Next Update: [TIME + 15 minutes] UTC

For questions, contact: [ON-CALL CONTACT]
```

### Progress Update

```
Subject: [UPDATE] ACGS2 Service Degradation - Failover In Progress

Severity: P1 - Critical
Status: Failover In Progress
Start Time: [TIME] UTC

Update:
- Application layer failover: COMPLETE
- Database failover: IN PROGRESS
- Kafka failover: PENDING

Estimated Time to Resolution: [TIME] UTC

Next Update: [TIME + 10 minutes] UTC
```

### Resolution Notification

```
Subject: [RESOLVED] ACGS2 Service Degradation - Failover Complete

Severity: P1 - Critical
Status: Resolved
Start Time: [TIME] UTC
End Time: [TIME] UTC
Duration: [DURATION]

Summary:
The service degradation in [PRIMARY_REGION] has been resolved through regional failover to [TARGET_REGION]. All services are now operating normally.

Root Cause:
[Brief description]

Impact Summary:
- Total downtime: [DURATION]
- Affected services: [LIST]
- Data loss: [NONE / amount]

Next Steps:
- Post-incident review scheduled for [DATE]
- Failback planned for [DATE] (if applicable)

For questions, contact: [ON-CALL CONTACT]
```

---

## Troubleshooting

### Application Issues

#### Traffic Not Shifting

```bash
# Check DestinationRule
kubectl get destinationrule -A --context=${TARGET_CONTEXT}

# Check VirtualService weights
kubectl get virtualservice -A -o yaml --context=${TARGET_CONTEXT} | grep -A 10 "weight"

# Check Envoy proxy logs
kubectl logs -l istio=ingressgateway -n istio-system --context=${TARGET_CONTEXT} --tail=100

# Force proxy refresh
kubectl exec -it deploy/claude-flow -n claude-flow-system --context=${TARGET_CONTEXT} -- \
  pilot-agent request POST /quitquitquit
```

#### Pods Not Starting

```bash
# Check events
kubectl get events -n claude-flow-system --sort-by='.lastTimestamp' --context=${TARGET_CONTEXT}

# Check resource constraints
kubectl describe pod -l app.kubernetes.io/name=claude-flow -n claude-flow-system --context=${TARGET_CONTEXT}

# Check node capacity
kubectl top nodes --context=${TARGET_CONTEXT}
```

### Database Issues

#### Standby Won't Promote

```bash
# Check PostgreSQL logs
kubectl logs postgresql-standby-0 -n database --context=${TARGET_CONTEXT} --tail=100

# Check for standby.signal file
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  ls -la /bitnami/postgresql/data/standby.signal

# Manual promotion via SQL
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_promote();"
```

#### Connection Errors After Promotion

```bash
# Check pg_hba.conf
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  cat /bitnami/postgresql/data/pg_hba.conf

# Reload configuration
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SELECT pg_reload_conf();"

# Check max_connections
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  psql -U postgres -c "SHOW max_connections;"
```

### Kafka Issues

#### MirrorMaker 2 Connector Failed

```bash
# Check connector status
kubectl exec -it deploy/mirrormaker2 -n kafka-system --context=${TARGET_CONTEXT} -- \
  curl -s http://localhost:8083/connectors/MirrorSourceConnector/status | jq

# Restart connector
kubectl exec -it deploy/mirrormaker2 -n kafka-system --context=${TARGET_CONTEXT} -- \
  curl -X POST http://localhost:8083/connectors/MirrorSourceConnector/restart

# Check connector logs
kubectl logs deploy/mirrormaker2 -n kafka-system --context=${TARGET_CONTEXT} --tail=100
```

#### Consumer Lag Increasing

```bash
# Check consumer group details
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9093 \
  --group acgs-agent-consumers --describe --verbose

# Check topic partition health
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-topics.sh --bootstrap-server localhost:9093 \
  --describe --topic acgs.agent.messages --under-replicated-partitions
```

---

## Emergency Contacts

### Escalation Path

| Level | Role | Contact | Response Time |
|-------|------|---------|---------------|
| L1 | On-Call Engineer | [PagerDuty] | 5 minutes |
| L2 | Team Lead | [Phone/Slack] | 15 minutes |
| L3 | Platform Manager | [Phone/Slack] | 30 minutes |
| L4 | VP Engineering | [Phone] | 1 hour |

### External Contacts

| Service | Contact | Purpose |
|---------|---------|---------|
| Cloud Provider Support | [Support Portal] | Infrastructure issues |
| Database Vendor | [Support Ticket] | PostgreSQL issues |
| Network Team | [Slack Channel] | DNS/Network changes |

### Runbook Maintenance

This runbook should be:
- Reviewed quarterly by the Platform Operations team
- Updated after each failover event
- Tested via tabletop exercises bi-annually
- Stored in version control with change tracking

---

## Appendix

### A. Quick Reference Commands

```bash
# === Application ===
# Shift traffic to target region
kubectl apply -f istio/traffic-shift-${TARGET_CONTEXT}.yaml --context=${PRIMARY_CONTEXT}

# Scale down primary
kubectl scale deployment --all --replicas=0 -n claude-flow-system --context=${PRIMARY_CONTEXT}

# === Database ===
# Check replication lag
kubectl exec -it postgresql-primary-0 -n database --context=${PRIMARY_CONTEXT} -- \
  psql -U postgres -c "SELECT replay_lag FROM pg_stat_replication;"

# Promote standby
kubectl exec -it postgresql-standby-0 -n database --context=${TARGET_CONTEXT} -- \
  pg_ctl promote -D /bitnami/postgresql/data

# === Kafka ===
# Check consumer lag
kubectl exec -it deploy/kafka-0 -n kafka-system --context=${TARGET_CONTEXT} -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9093 --group acgs-agent-consumers --describe

# === Verification ===
# Run failover test
./acgs2-infra/multi-region/scripts/test-failover.sh --verbose ${PRIMARY_CONTEXT} ${TARGET_CONTEXT}
```

### B. Region-Specific Configuration

| Region | Context | Primary DB | Kafka Bootstrap |
|--------|---------|------------|-----------------|
| US-East-1 | us-east-1 | postgresql-primary.database:5432 | kafka.kafka-system:9093 |
| EU-West-1 | eu-west-1 | postgresql-standby.database:5432 | kafka.kafka-system:9093 |
| AP-Southeast-1 | ap-southeast-1 | postgresql-standby.database:5432 | kafka.kafka-system:9093 |

### C. Related Documentation

- [Multi-Region Deployment Guide](../README.md)
- [Istio Multi-Cluster Setup](../istio/README.md)
- [PostgreSQL Replication Configuration](../database/README.md)
- [Kafka MirrorMaker 2 Configuration](../kafka/README.md)
- [Tenant Residency Policies](../governance/README.md)
- [Compliance Verification](../compliance/README.md)

---

*Document End*
