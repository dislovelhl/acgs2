# ACGS-2 Air-Gapped Deployment Guide

**Constitutional Hash: cdd01ef066bc6cf2**

This guide provides comprehensive instructions for deploying ACGS-2 in air-gapped (offline) environments where external internet connectivity is restricted or prohibited. This deployment model is essential for:

- **Government and Defense**: Classified networks and secure facilities
- **Financial Services**: Regulated environments with strict data sovereignty requirements
- **Healthcare**: Protected Health Information (PHI) compliance
- **Critical Infrastructure**: Utilities, transportation, and industrial control systems
- **Highly Secure Enterprises**: Zero-trust architectures and offline operations

## 📋 Prerequisites

### Infrastructure Requirements

#### Hardware Specifications
```
Minimum Production Configuration:
- 3x Control Plane Nodes: 8 CPU cores, 32GB RAM, 500GB SSD each
- 5x Worker Nodes: 16 CPU cores, 64GB RAM, 1TB SSD each
- 1x Storage Node: 8 CPU cores, 32GB RAM, 4TB SSD
- Network: 10Gbps internal connectivity

Recommended Enterprise Configuration:
- 5x Control Plane Nodes: 16 CPU cores, 64GB RAM, 1TB SSD each
- 10x Worker Nodes: 32 CPU cores, 128GB RAM, 2TB SSD each
- 3x Storage Nodes: 16 CPU cores, 64GB RAM, 8TB SSD each
- Network: 25Gbps+ internal connectivity with redundant paths
```

#### Software Requirements
- **Kubernetes**: v1.28+ with security hardening
- **Container Runtime**: Containerd 1.7+ or CRI-O 1.26+
- **Network Plugin**: Calico 3.26+ or Cilium 1.13+
- **Storage**: Ceph 17+ or Longhorn 1.5+ (air-gapped compatible)
- **Load Balancer**: MetalLB 0.13+ or HAProxy 2.8+

### Security Clearance Requirements

#### Personnel Requirements
- **System Administrators**: Secret/Top Secret clearance (depending on data classification)
- **Security Officers**: Must hold appropriate security certifications
- **Auditors**: Access to system logs and audit trails

#### System Accreditation
- **Security Assessment**: Independent security assessment required
- **Authorization Boundary**: Clearly defined system boundaries
- **Configuration Management**: Strict change control processes
- **Continuous Monitoring**: 24/7 security monitoring and alerting

## 🚀 Deployment Architecture

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Air-Gapped Network Boundary                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DMZ (Demilitarized Zone)               │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │        Application Zone (ACGS-2 Core)       │    │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │    │    │
│  │  │  │  API    │ │ Agent   │ │ Policy  │        │    │    │
│  │  │  │ Gateway │ │  Bus    │ │ Engine  │        │    │    │
│  │  │  └─────────┘ └─────────┘ └─────────┘        │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │         Data Zone (Databases & Storage)     │    │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │    │    │
│  │  │  │PostgreSQL│ │  Redis  │ │ MinIO   │        │    │    │
│  │  │  │ Cluster │ │ Cluster │ │ (S3)    │        │    │    │
│  │  │  └─────────┘ └─────────┘ └─────────┘        │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Management Zone                       │    │    │
│  │  (Bastion hosts, monitoring, logging)               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Component Isolation

#### Network Security Zones
1. **External Boundary**: Internet-facing components (if any)
2. **DMZ**: Reverse proxies, load balancers, WAF
3. **Application Zone**: ACGS-2 core services
4. **Data Zone**: Databases, caches, object storage
5. **Management Zone**: Administrative access, monitoring

#### Security Controls
- **Zero Trust**: Every request authenticated and authorized
- **Network Segmentation**: VLAN isolation between zones
- **Access Control**: Mandatory access controls (MAC)
- **Encryption**: End-to-end encryption for all data in transit

## 📦 Offline Package Preparation

### Container Registry Setup

#### 1. Internal Registry Configuration

```bash
# Create internal container registry
kubectl create namespace registry

# Deploy Harbor registry (air-gapped compatible)
helm install harbor harbor/harbor \
  --namespace registry \
  --set expose.type=clusterIP \
  --set persistence.enabled=true \
  --set persistence.persistentVolumeClaim.registry.size=500Gi \
  --set persistence.persistentVolumeClaim.chartmuseum.size=100Gi \
  --set persistence.persistentVolumeClaim.jobservice.size=100Gi \
  --set persistence.persistentVolumeClaim.database.size=100Gi
```

#### 2. Image Mirroring Process

```bash
# On internet-connected machine
docker pull acgs2/agent-bus:3.0.0
docker pull acgs2/api-gateway:3.0.0
docker pull acgs2/policy-registry:3.0.0
docker pull acgs2/audit-service:3.0.0
docker pull acgs2/tenant-management:3.0.0
docker pull acgs2/agent-inventory:3.0.0

# Save images to tar files
docker save acgs2/agent-bus:3.0.0 > agent-bus-3.0.0.tar
docker save acgs2/api-gateway:3.0.0 > api-gateway-3.0.0.tar

# Transfer to air-gapped environment via secure media
```

#### 3. Load Images in Air-Gapped Environment

```bash
# Load images into internal registry
docker load < agent-bus-3.0.0.tar
docker tag acgs2/agent-bus:3.0.0 internal-registry:5000/acgs2/agent-bus:3.0.0
docker push internal-registry:5000/acgs2/agent-bus:3.0.0
```

### Dependency Management

#### 1. Helm Chart Repository

```bash
# Create internal Helm repository
helm plugin install https://github.com/chartmuseum/helm-push
helm repo add internal http://internal-registry:8080
```

#### 2. Package Mirroring

```bash
# Mirror required Helm charts
helm pull bitnami/postgresql --version 12.1.6 --destination ./charts/
helm pull bitnami/redis --version 17.3.3 --destination ./charts/
helm pull prometheus-community/prometheus --version 15.0.0 --destination ./charts/

# Transfer to air-gapped environment
```

## 🔧 Installation Process

### Phase 1: Infrastructure Setup

#### 1. Kubernetes Cluster Deployment

```bash
# Initialize Kubernetes cluster (using kubeadm)
kubeadm init --pod-network-cidr=10.244.0.0/16 \
  --service-cidr=10.96.0.0/12 \
  --apiserver-advertise-address=INTERNAL_IP \
  --control-plane-endpoint=CLUSTER_ENDPOINT

# Deploy network plugin (Calico)
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Join worker nodes
kubeadm join CLUSTER_ENDPOINT --token TOKEN --discovery-token-ca-cert-hash SHA256:HASH
```

#### 2. Storage Configuration

```bash
# Deploy Ceph storage cluster
kubectl apply -f ceph-cluster.yaml

# Create storage classes
kubectl apply -f storage-classes.yaml
```

#### 3. Ingress Controller

```bash
# Deploy NGINX Ingress Controller (internal registry)
helm install nginx-ingress internal/nginx-ingress \
  --namespace ingress \
  --set controller.image.registry=internal-registry:5000 \
  --set controller.image.repository=nginx-ingress/controller
```

### Phase 2: Security Hardening

#### 1. Pod Security Standards

```bash
# Apply restricted pod security standards
kubectl apply -f pod-security-standards.yaml

# Configure Kyverno policies
kubectl apply -f kyverno-policies.yaml
```

#### 2. Network Policies

```bash
# Apply comprehensive network policies
kubectl apply -f network-policies.yaml
```

#### 3. Certificate Management

```bash
# Deploy cert-manager with internal CA
kubectl apply -f cert-manager.yaml
kubectl apply -f internal-ca-issuer.yaml
```

### Phase 3: Database Deployment

#### 1. PostgreSQL Cluster

```bash
# Deploy PostgreSQL using mirrored charts
helm install postgresql internal/postgresql \
  --namespace database \
  --values postgresql-airgapped-values.yaml
```

#### 2. Redis Cluster

```bash
# Deploy Redis cluster
helm install redis internal/redis \
  --namespace database \
  --values redis-airgapped-values.yaml
```

#### 3. Kafka (Optional)

```bash
# Deploy Kafka for event streaming
helm install kafka internal/kafka \
  --namespace messaging \
  --values kafka-airgapped-values.yaml
```

### Phase 4: ACGS-2 Core Deployment

#### 1. Namespace Creation

```bash
# Create ACGS-2 namespaces
kubectl create namespace acgs2-system
kubectl create namespace acgs2-monitoring
kubectl create namespace acgs2-security
```

#### 2. Helm Deployment

```bash
# Deploy ACGS-2 using air-gapped configuration
helm install acgs2 ./acgs2-helm-chart \
  --namespace acgs2-system \
  --values airgapped-values.yaml \
  --set global.imageRegistry=internal-registry:5000
```

#### 3. Post-Deployment Configuration

```bash
# Wait for deployment to complete
kubectl wait --for=condition=available --timeout=600s deployment/acgs2-enhanced-agent-bus -n acgs2-system

# Run post-deployment checks
kubectl exec -it deployment/acgs2-enhanced-agent-bus -n acgs2-system -- /app/scripts/health-check.sh

# Initialize tenant
kubectl exec -it deployment/acgs2-tenant-management -n acgs2-system -- /app/scripts/init-tenant.sh
```

## 🔐 Security Configuration

### Certificate Management

#### Internal Certificate Authority

```yaml
# internal-ca-issuer.yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: internal-ca-issuer
  namespace: cert-manager
spec:
  ca:
    secretName: internal-ca-key-pair
```

#### TLS Certificate Generation

```bash
# Generate certificates for internal services
cert-manager controller generate \
  --issuer internal-ca-issuer \
  --dns-names acgs2.internal.company.com \
  --output tls.crt,tls.key
```

### Authentication & Authorization

#### 1. OIDC Configuration (Internal)

```yaml
# Configure internal OIDC provider
oidc:
  enabled: true
  issuerUrl: "https://internal-oidc.company.com"
  clientId: "acgs2-client"
  clientSecret: "internal-client-secret"
  scopes: ["openid", "profile", "email", "groups"]
```

#### 2. RBAC Configuration

```yaml
# Enhanced RBAC policies for air-gapped environment
rbac:
  strictMode: true
  auditAllAccess: true
  sessionTimeout: 3600  # 1 hour
  maxLoginAttempts: 3
  lockoutDuration: 900  # 15 minutes
```

### Data Protection

#### Encryption at Rest

```yaml
# Configure encryption for all persistent volumes
encryption:
  enabled: true
  kms:
    provider: internal-kms
    keyId: acgs2-encryption-key
  algorithm: AES256
```

#### Network Encryption

```bash
# Enable mTLS for all service communication
kubectl apply -f mtls-policies.yaml

# Configure Istio for service mesh encryption
kubectl apply -f istio-security-policies.yaml
```

## 📊 Monitoring & Observability

### Internal Monitoring Stack

#### 1. Prometheus Deployment

```bash
# Deploy Prometheus with internal configuration
helm install prometheus internal/prometheus \
  --namespace acgs2-monitoring \
  --values prometheus-airgapped-values.yaml
```

#### 2. Grafana Configuration

```bash
# Deploy Grafana with pre-configured dashboards
helm install grafana internal/grafana \
  --namespace acgs2-monitoring \
  --values grafana-airgapped-values.yaml
```

#### 3. Logging Aggregation

```bash
# Deploy ELK stack for log aggregation
helm install elasticsearch internal/elasticsearch \
  --namespace acgs2-monitoring

helm install logstash internal/logstash \
  --namespace acgs2-monitoring

helm install kibana internal/kibana \
  --namespace acgs2-monitoring
```

### Alerting Configuration

#### 1. Alert Manager

```yaml
# alertmanager-config.yaml
global:
  smtp_smtp: "internal-smtp.company.com"
  smtp_from: "alerts@company.com"

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'internal-alerts'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'

receivers:
- name: 'internal-alerts'
  email_configs:
  - to: 'security-team@company.com'
    subject: 'ACGS-2 Alert: {{ .GroupLabels.alertname }}'
```

## 🔄 Backup & Recovery

### Automated Backup Strategy

#### 1. Database Backups

```bash
# Configure automated PostgreSQL backups
kubectl apply -f postgresql-backup-cronjob.yaml

# Configure backup to internal storage
backup:
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention: 30
  storage:
    type: internal-nfs
    path: /backups/acgs2/database
  encryption:
    enabled: true
    key: internal-encryption-key
```

#### 2. Configuration Backups

```bash
# Backup Helm releases and configurations
helm plugin install https://github.com/databus23/helm-diff
helm backup all --namespace acgs2-system --output /backups/helm-releases/
```

#### 3. Container Image Backups

```bash
# Mirror running images to backup registry
kubectl get pods -n acgs2-system -o jsonpath='{.items[*].spec.containers[*].image}' | \
  tr ' ' '\n' | sort | uniq | \
  xargs -I {} docker pull {} && \
  docker save {} | gzip > /backups/images/$(basename {}).tar.gz
```

### Disaster Recovery

#### 1. Recovery Procedures

```bash
# Complete system recovery procedure
#!/bin/bash
# acgs2-disaster-recovery.sh

echo "Starting ACGS-2 disaster recovery..."

# 1. Restore infrastructure
kubectl apply -f infrastructure-backup.yaml

# 2. Restore persistent volumes
kubectl apply -f pv-restore.yaml

# 3. Restore databases
pg_restore -h postgresql-cluster -U acgs2 -d acgs2 /backups/database/latest.dump

# 4. Restore configurations
helm upgrade --install acgs2 ./acgs2-backup-chart -n acgs2-system

# 5. Verify system integrity
kubectl exec -it deployment/acgs2-health-check -n acgs2-system -- /app/scripts/verify-recovery.sh

echo "ACGS-2 disaster recovery completed."
```

## 🔍 Compliance & Auditing

### Audit Configuration

#### 1. Audit Logging

```yaml
# Enhanced audit configuration for air-gapped environment
audit:
  enabled: true
  immutable: true
  retention: 2555  # 7 years
  storage:
    type: tamper-proof-storage
    encryption: true
  realTimeMonitoring: true
  alerts:
    enabled: true
    destinations:
      - internal-siem
      - security-dashboard
```

#### 2. Compliance Reporting

```bash
# Generate compliance reports
kubectl exec -it deployment/acgs2-audit-service -n acgs2-system -- \
  /app/scripts/generate-compliance-report.sh \
    --framework SOC2 \
    --period last_quarter \
    --output /reports/soc2-compliance-$(date +%Y%m%d).pdf
```

### Security Assessment

#### 1. Vulnerability Scanning

```bash
# Regular vulnerability scans
kubectl apply -f vulnerability-scan-cronjob.yaml

# Scan container images
trivy image --format json internal-registry:5000/acgs2/agent-bus:3.0.0 > vulnerability-report.json
```

#### 2. Configuration Compliance

```bash
# CIS Kubernetes benchmark compliance
kube-bench run --targets master,etcd,controlplane,worker,managedservices,policies
```

## 🚨 Emergency Procedures

### Security Incident Response

#### 1. Incident Detection

```bash
# Monitor for security incidents
kubectl logs -f deployment/acgs2-security-monitor -n acgs2-security

# Check for policy violations
kubectl exec -it deployment/acgs2-policy-engine -n acgs2-system -- \
  /app/scripts/check-violations.sh --last-1h
```

#### 2. Incident Containment

```bash
# Emergency lockdown procedure
#!/bin/bash
# acgs2-emergency-lockdown.sh

echo "Initiating ACGS-2 emergency lockdown..."

# 1. Isolate affected components
kubectl scale deployment affected-service --replicas=0 -n acgs2-system

# 2. Enable emergency policies
kubectl apply -f emergency-security-policies.yaml

# 3. Notify security team
curl -X POST internal-alerts.company.com \
  -H "Content-Type: application/json" \
  -d '{"alert": "ACGS-2 Security Incident", "severity": "critical"}'

# 4. Preserve evidence
kubectl exec -it deployment/acgs2-forensic-collector -n acgs2-security -- \
  /app/scripts/collect-evidence.sh --incident-id $(date +%s)

echo "Emergency lockdown initiated. Awaiting security team response."
```

### System Maintenance

#### 1. Patch Management

```bash
# Automated patch deployment
kubectl apply -f patch-management-cronjob.yaml

# Rolling update procedure
kubectl rollout restart deployment/acgs2-enhanced-agent-bus -n acgs2-system
kubectl rollout status deployment/acgs2-enhanced-agent-bus -n acgs2-system
```

#### 2. Capacity Planning

```bash
# Monitor resource utilization
kubectl top nodes
kubectl top pods -n acgs2-system

# Generate capacity reports
/app/scripts/capacity-planning.sh --output /reports/capacity-$(date +%Y%m%d).html
```

## 📞 Support & Maintenance

### Internal Support Structure

#### 1. Support Team
- **Primary**: Internal DevOps/Security team
- **Secondary**: ACGS-2 vendor support (approved channels only)
- **Escalation**: CISO and senior leadership

#### 2. Documentation
- **Runbooks**: Detailed operational procedures
- **Knowledge Base**: Internal wiki with troubleshooting guides
- **Change Management**: Approved change procedures

#### 3. Training
- **Initial Training**: 40 hours for administrators
- **Annual Refresher**: Security awareness and procedures
- **Certification**: Required security certifications

### Maintenance Windows

```yaml
# Scheduled maintenance windows
maintenance:
  weekly:
    day: sunday
    start: "02:00"
    duration: "4h"
  monthly:
    day: "first-sunday"
    start: "01:00"
    duration: "8h"
  emergency:
    approval_required: true
    notification: "immediate"
```

---

## 📋 Checklist

### Pre-Deployment
- [ ] Security clearance verification completed
- [ ] System accreditation obtained
- [ ] Network boundary definition approved
- [ ] Internal CA certificates generated
- [ ] Container images mirrored to internal registry
- [ ] Dependency packages downloaded and verified

### Deployment
- [ ] Infrastructure provisioning completed
- [ ] Kubernetes cluster hardened and secured
- [ ] Storage and networking configured
- [ ] Security policies applied
- [ ] Databases and caches deployed
- [ ] ACGS-2 core services installed
- [ ] Monitoring and alerting configured

### Post-Deployment
- [ ] System functionality verified
- [ ] Security assessment completed
- [ ] User access configured
- [ ] Backup procedures tested
- [ ] Documentation updated
- [ ] Team training completed

### Ongoing Operations
- [ ] Regular security scans scheduled
- [ ] Backup integrity verified weekly
- [ ] Performance monitoring active
- [ ] Audit logs reviewed regularly
- [ ] Compliance reports generated quarterly

---

**⚠️ Critical Notes:**

1. **No Internet Access**: All components must be pre-downloaded and mirrored
2. **Security First**: Every procedure must maintain security boundaries
3. **Audit Everything**: All actions must be logged and auditable
4. **Test Recovery**: Disaster recovery must be tested regularly
5. **Change Control**: All changes require formal approval processes

For additional support or custom air-gapped configurations, contact the ACGS-2 Enterprise Support team.
