# ACGS-2 Multi-Region Infrastructure Operations Guide

**Version:** 1.0.0
**Last Updated:** 2026-01-02
**Constitutional Hash:** cdd01ef066bc6cf2

This guide provides comprehensive operational procedures for managing ACGS-2's multi-region infrastructure, including deployment, monitoring, failover, and disaster recovery.

## 🏗️ Architecture Overview

### Multi-Region Components

```
Global Traffic Management (Cloudflare)
    ↓
┌─────────────────────────────────────┐
│         Region 1 (us-east-1)        │
│  ┌─────────────┐ ┌─────────────┐    │
│  │   Control   │ │   Data      │    │
│  │   Plane     │ │   Plane     │    │
│  │             │ │             │    │
│  │ • Istio CP  │ │ • PostgreSQL│    │
│  │ • Services  │ │ • Redis     │    │
│  │ • Kafka     │ │ • S3        │    │
│  └─────────────┘ └─────────────┘    │
└─────────────────────────────────────┘
           │          │
           │          │
           ▼          ▼
┌─────────────────────────────────────┐
│         Region 2 (eu-west-1)        │
│  ┌─────────────┐ ┌─────────────┐    │
│  │   Control   │ │   Data      │    │
│  │   Plane     │ │   Data      │    │
│  │             │ │   Replica   │    │
│  │ • Istio CP  │ │ • PostgreSQL│    │
│  │ • Services  │ │ • Redis     │    │
│  │ • Kafka     │ │ • S3        │    │
│  └─────────────┘ └─────────────┘    │
└─────────────────────────────────────┘
```

### Key Technologies

- **Service Mesh:** Istio Multi-Primary Multi-Network
- **Database:** PostgreSQL Physical Streaming Replication
- **Cache:** Redis Active-Active Global Replication
- **Messaging:** Kafka with MirrorMaker 2
- **Governance:** OPA with tenant residency policies

## 🚀 Deployment Procedures

### Prerequisites

#### Infrastructure Requirements
```bash
# Required tools
istioctl version  # 1.22.0+
kubectl version   # 1.28+
helm version      # 3.14+
kustomize version # 5.2+

# Required permissions
# - Kubernetes cluster admin in both regions
# - AWS/GCP/Azure cross-region networking
# - DNS management access
```

#### Network Prerequisites
```bash
# Verify non-overlapping Pod CIDR ranges
kubectl --context=region1 cluster-info dump | grep cluster-cidr
kubectl --context=region2 cluster-info dump | grep cluster-cidr

# Expected: Different ranges (e.g., 10.244.0.0/16 vs 10.245.0.0/16)
```

### Phase 1: Istio Multi-Cluster Foundation

#### 1. Generate Shared Root CA
```bash
cd acgs2-infra/multi-region/istio
./shared-root-ca-setup.sh

# Verify CA creation
ls -la ca/
# Expected: ca-cert.pem, ca-key.pem, region1-ca-secret.yaml, region2-ca-secret.yaml
```

#### 2. Deploy Istio Control Planes
```bash
# Apply CA secrets to both clusters
kubectl apply -f ca/region1-ca-secret.yaml --context=region1
kubectl apply -f ca/region2-ca-secret.yaml --context=region2

# Install Istio in Region 1
istioctl install --context=region1 -f istio-operator-region1.yaml

# Install Istio in Region 2
istioctl install --context=region2 -f istio-operator-region2.yaml

# Verify installations
istioctl proxy-status --context=region1
istioctl proxy-status --context=region2
```

#### 3. Configure Cross-Cluster Communication
```bash
# Create remote secrets for cross-cluster access
istioctl create-remote-secret --context=region1 --name=cluster1 | \
  kubectl apply --context=region2 -f -

istioctl create-remote-secret --context=region2 --name=cluster2 | \
  kubectl apply --context=region1 -f -

# Label namespaces with network topology
kubectl label namespace istio-system topology.istio.io/network=network1 --context=region1
kubectl label namespace default topology.istio.io/network=network1 --context=region1

kubectl label namespace istio-system topology.istio.io/network=network2 --context=region2
kubectl label namespace default topology.istio.io/network=network2 --context=region2
```

#### 4. Apply Locality Load Balancing
```bash
kubectl apply -f locality-load-balancing.yaml --context=region1
kubectl apply -f locality-load-balancing.yaml --context=region2
```

### Phase 2: Database Layer

#### 1. Deploy PostgreSQL Primary (Region 1)
```bash
cd acgs2-infra/multi-region/database

# Deploy primary database
helm install postgresql-primary bitnami/postgresql \
  -f postgresql-primary-values.yaml \
  --namespace database \
  --create-namespace \
  --context=region1

# Wait for primary to be ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=postgresql \
  --namespace database \
  --context=region1 \
  --timeout=300s
```

#### 2. Deploy PostgreSQL Standby (Region 2)
```bash
# Deploy standby replica
helm install postgresql-standby bitnami/postgresql \
  -f postgresql-standby-values.yaml \
  --namespace database \
  --create-namespace \
  --context=region2

# Verify replication
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

#### 3. Monitor Replication Health
```bash
# Check replication lag
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "
    SELECT
      application_name,
      state,
      sync_state,
      EXTRACT(EPOCH FROM (now() - replay_timestamp)) as lag_seconds
    FROM pg_stat_replication;
  "
```

### Phase 3: Service Deployment

#### 1. Deploy claude-flow Service
```bash
cd acgs2-infra/multi-region/k8s

# Deploy to Region 1
helm install claude-flow-region1 ./multi-region-deployment-claude-flow.yaml \
  --namespace default \
  --set region=us-east-1 \
  --set networkId=1 \
  --context=region1

# Deploy to Region 2
helm install claude-flow-region2 ./multi-region-deployment-claude-flow.yaml \
  --namespace default \
  --set region=eu-west-1 \
  --set networkId=2 \
  --context=region2
```

#### 2. Deploy neural-mcp Service
```bash
# Deploy to Region 1 with GPU support
helm install neural-mcp-region1 ./multi-region-deployment-neural-mcp.yaml \
  --namespace default \
  --set region=us-east-1 \
  --set networkId=1 \
  --set gpu.enabled=true \
  --context=region1

# Deploy to Region 2
helm install neural-mcp-region2 ./multi-region-deployment-neural-mcp.yaml \
  --namespace default \
  --set region=eu-west-1 \
  --set networkId=2 \
  --set gpu.enabled=false \
  --context=region2
```

### Phase 4: Compliance and Governance

#### 1. Deploy Tenant Residency Configuration
```bash
cd acgs2-infra/multi-region/governance

# Deploy configuration to both regions
kubectl apply -f tenant-residency-config.yaml --context=region1
kubectl apply -f tenant-residency-config.yaml --context=region2
```

#### 2. Deploy OPA Policies
```bash
# Apply residency policies
kubectl apply -f opa-residency-policy.rego --context=region1
kubectl apply -f opa-residency-policy.rego --context=region2
```

#### 3. Deploy Compliance Verification
```bash
cd acgs2-infra/multi-region/compliance

# Deploy CronJob to both regions
kubectl apply -f compliance-verification-cronjob.yaml --context=region1
kubectl apply -f compliance-verification-cronjob.yaml --context=region2
```

### Phase 5: Event Streaming

#### 1. Deploy Kafka MirrorMaker 2
```bash
cd acgs2-infra/multi-region/kafka

# Deploy MirrorMaker 2
kubectl apply -f kafka-mirrormaker2.yaml --context=region1
kubectl apply -f kafka-mirrormaker2.yaml --context=region2
```

## 📊 Monitoring and Observability

### Health Checks

#### Istio Control Plane Health
```bash
# Check proxy status
istioctl proxy-status --context=region1
istioctl proxy-status --context=region2

# Verify cross-cluster connectivity
istioctl pc endpoints --context=region1 \
  --cluster cluster2 \
  --service claude-flow.default.svc.cluster.local
```

#### Database Replication Health
```bash
# Replication lag monitoring
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "
    SELECT
      application_name,
      state,
      sync_state,
      EXTRACT(EPOCH FROM (now() - replay_timestamp)) as lag_seconds,
      pg_wal_lss_diff(pg_current_wal_lss(), restart_lss) as retained_wal_bytes
    FROM pg_stat_replication;
  "
```

#### Service Health
```bash
# Check pod status across regions
kubectl get pods --all-namespaces --context=region1
kubectl get pods --all-namespaces --context=region2

# Verify service endpoints
kubectl get endpoints --all-namespaces --context=region1
kubectl get endpoints --all-namespaces --context=region2
```

### Key Metrics to Monitor

#### Performance Metrics
```bash
# Istio metrics
kubectl port-forward -n istio-system svc/istio-telemetry 42422:42422 --context=region1 &
curl "http://localhost:42422/metrics" | grep istio_requests_total

# Database metrics
kubectl port-forward -n database svc/postgresql-primary-metrics 9187:9187 --context=region1 &
curl "http://localhost:9187/metrics" | grep pg_replication_lag
```

#### Business Metrics
- Cross-region request latency (P95 < 100ms)
- Replication lag (< 60 seconds)
- Service availability (99.9% SLA)
- Compliance violation count (target: 0)

## 🚨 Failover and Disaster Recovery

### Regional Failover Procedures

#### Automatic Failover (< 60 seconds)
```bash
# 1. Simulate region failure (for testing)
kubectl --context=region1 scale deployment claude-flow --replicas=0

# 2. Monitor failover
kubectl --context=region2 logs -f deployment/claude-flow-region2

# 3. Verify traffic shift
istioctl pc routes --context=region2 \
  --name claude-flow.default.svc.cluster.local \
  | grep weight
```

#### Manual Failover (when automatic fails)
```bash
# 1. Update DNS to point to healthy region
# Update Route 53 or Cloudflare configuration

# 2. Scale down unhealthy region
kubectl --context=region1 scale deployment --all --replicas=0

# 3. Promote standby database
kubectl exec -it postgresql-standby-postgresql-0 \
  --namespace database \
  --context=region2 \
  -- psql -U postgres -c "
    SELECT pg_promote();
    ALTER SYSTEM SET synchronous_standby_names = '';
    SELECT pg_reload_conf();
  "

# 4. Update application configuration
kubectl --context=region2 set env deployment/claude-flow-region2 \
  PRIMARY_REGION=eu-west-1
```

### Database Failover Procedures

#### Primary Database Failure
```bash
# 1. Detect failure (via monitoring alerts)
# 2. Confirm primary is down
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "SELECT 1;" || echo "Primary is down"

# 3. Promote standby to primary
kubectl exec -it postgresql-standby-postgresql-0 \
  --namespace database \
  --context=region2 \
  -- psql -U postgres -c "
    SELECT pg_promote();
    ALTER SYSTEM SET synchronous_standby_names = '';
    SELECT pg_reload_conf();
  "

# 4. Update DNS and service endpoints
# Point applications to new primary in Region 2

# 5. Rebuild replication (when original region recovers)
# Deploy new standby in recovered region
```

### Complete Region Recovery

#### Recovery Steps
```bash
# 1. Restore region infrastructure
# 2. Deploy services in recovery mode
# 3. Configure as new standby region
# 4. Re-establish replication
# 5. Test failover procedures
# 6. Update DNS for load balancing
```

## 🔧 Maintenance Procedures

### Certificate Rotation
```bash
# Rotate Istio certificates
istioctl x cert-manager check --context=region1

# Rotate shared root CA
cd acgs2-infra/multi-region/istio
./shared-root-ca-setup.sh
kubectl apply -f ca/region1-ca-secret.yaml --context=region1
kubectl apply -f ca/region2-ca-secret.yaml --context=region2
```

### Database Maintenance
```bash
# Vacuum and analyze
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "VACUUM ANALYZE;"

# Monitor WAL disk usage
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "
    SELECT
      slot_name,
      pg_wal_lss_diff(pg_current_wal_lss(), restart_lss) as retained_bytes,
      pg_size_pretty(pg_wal_lss_diff(pg_current_wal_lss(), restart_lss)) as size
    FROM pg_replication_slots;
  "
```

### Service Updates
```bash
# Rolling update with zero downtime
kubectl set image deployment/claude-flow \
  claude-flow=acgs2/claude-flow:v2.0.0 \
  --context=region1

# Verify update
kubectl rollout status deployment/claude-flow --context=region1
```

## 🔍 Troubleshooting

### Common Issues

#### Cross-Cluster Communication Problems
```bash
# Check remote secrets
kubectl get secrets -n istio-system --context=region1 | grep istio-remote

# Verify network policies
istioctl pc listeners --context=region1 \
  --address 0.0.0.0 --port 15443

# Check East-West Gateway logs
kubectl logs -n istio-system \
  -l app=istio-eastwestgateway \
  --context=region1
```

#### Database Replication Issues
```bash
# Check replication status
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Check standby status
kubectl exec -it postgresql-standby-postgresql-0 \
  --namespace database \
  --context=region2 \
  -- psql -U postgres -c "SELECT pg_is_in_recovery();"

# Reset replication slot if needed
kubectl exec -it postgresql-primary-postgresql-0 \
  --namespace database \
  --context=region1 \
  -- psql -U postgres -c "
    SELECT pg_drop_replication_slot('acgs2_standby_slot');
    SELECT pg_create_physical_replication_slot('acgs2_standby_slot');
  "
```

#### Compliance Violations
```bash
# Check compliance logs
kubectl logs -l app=acgs2-compliance-verification --context=region1

# Verify tenant configuration
kubectl get configmap tenant-residency-config -o yaml --context=region1

# Test OPA policies
kubectl exec -it opa-pod --context=region1 -- opa test policy.rego
```

## 📈 Scaling Procedures

### Horizontal Scaling
```bash
# Scale claude-flow service
kubectl scale deployment claude-flow-region1 \
  --replicas=10 \
  --context=region1

# Scale neural-mcp with GPU
kubectl scale deployment neural-mcp-region1 \
  --replicas=5 \
  --context=region1
```

### Vertical Scaling
```bash
# Update resource limits
kubectl set resources deployment claude-flow \
  --limits=cpu=2000m,memory=4Gi \
  --requests=cpu=500m,memory=1Gi \
  --context=region1
```

### Adding New Regions
```bash
# 1. Provision new Kubernetes cluster
# 2. Generate CA secret for new region
# 3. Create new IstioOperator manifest
# 4. Deploy PostgreSQL standby
# 5. Configure MirrorMaker 2
# 6. Update locality load balancing
# 7. Update compliance verification
```

## 📋 Compliance and Security

### Data Residency Verification
```bash
# Run compliance check manually
kubectl create job compliance-check-$(date +%s) \
  --from=cronjob/acgs2-compliance-verification \
  --context=region1

# Check results
kubectl logs job/compliance-check-$(date +%s) --context=region1
```

### Security Audits
```bash
# Audit network policies
kubectl get networkpolicies --all-namespaces --context=region1

# Check RBAC
kubectl get roles,rolebindings --all-namespaces --context=region1

# Verify mTLS
istioctl authn tls-check pod-name.namespace --context=region1
```

## 📞 Support and Escalation

### Alert Classifications

- **P0 (Critical):** Complete region failure, data loss, security breach
- **P1 (High):** Service degradation >50%, replication lag >5min
- **P2 (Medium):** Performance degradation, monitoring alerts
- **P3 (Low):** Informational, maintenance notifications

### Contact Information

- **Platform Team:** platform@acgs2.com
- **Security Team:** security@acgs2.com
- **Database Team:** database@acgs2.com
- **Network Team:** network@acgs2.com

### Emergency Procedures

1. Assess impact and classify incident
2. Notify stakeholders based on severity
3. Follow appropriate runbook procedures
4. Document incident and resolution
5. Conduct post-mortem analysis

---

**Document Version Control:**
- v1.0.0: Initial multi-region operations guide
- Based on spec 020-multi-region-global-deployment-support
- Constitutional Hash: cdd01ef066bc6cf2
