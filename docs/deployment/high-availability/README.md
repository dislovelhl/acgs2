# ACGS-2 High-Availability Deployment Guide

**Constitutional Hash: cdd01ef066bc6cf2**

This guide provides comprehensive instructions for deploying ACGS-2 in high-availability (HA) configurations designed for mission-critical enterprise environments requiring 99.99%+ uptime, zero-downtime deployments, and automatic failure recovery.

## 🎯 HA Objectives

### Service Level Agreements (SLAs)

- **Availability**: 99.99% (52.56 minutes downtime/year)
- **Recovery Time Objective (RTO)**: < 5 minutes
- **Recovery Point Objective (RPO)**: < 1 minute
- **Performance**: P99 latency < 5ms for API calls
- **Data Durability**: 99.999999999% (11 9's)

### Failure Scenarios Covered

- **Single Node Failure**: Automatic failover within 30 seconds
- **AZ/Region Failure**: Cross-zone replication and failover
- **Network Partition**: Split-brain prevention and recovery
- **Storage Failure**: Multi-zone replication and reconstruction
- **Application Crashes**: Automatic restart and health checks
- **Database Corruption**: Point-in-time recovery and validation

## 🏗️ Architecture Overview

### Multi-Zone Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Global Load Balancer                     │
│                    (CloudFlare/Global GLB)                  │
└─────────────────────┬─────────────────────┬─────────────────┘
                      │                     │
           ┌──────────▼─────────┐ ┌─────────▼─────────┐
           │   Region 1 (us-east-1) │ │ Region 2 (us-west-2) │
           │  ┌─────────────────┐ │ │ ┌─────────────────┐ │
           │  │   Zone A        │ │ │ │   Zone A        │ │
           │  │  ┌─────────┐    │ │ │ │  ┌─────────┐    │ │
           │  │  │ Control │    │ │ │ │  │ Control │    │ │
           │  │  │ Plane   │    │ │ │ │  │ Plane   │    │ │
           │  │  └─────────┘    │ │ │ │  └─────────┘    │ │
           │  └─────────────────┘ │ │ └─────────────────┘ │
           │  ┌─────────────────┐ │ │ ┌─────────────────┐ │
           │  │   Zone B        │ │ │ │   Zone B        │ │
           │  │  ┌─────────┐    │ │ │ │  ┌─────────┐    │ │
           │  │  │Workers  │    │ │ │ │  │Workers  │    │ │
           │  │  │& Data   │    │ │ │ │  │& Data   │    │ │
           │  │  └─────────┘    │ │ │ │  └─────────┘    │ │
           │  └─────────────────┘ │ │ └─────────────────┘ │
           └──────────────────────┘ └─────────────────────┘
```

### Component Redundancy

#### Control Plane HA

- **Kubernetes API Server**: 3+ replicas across zones
- **etcd**: 5-node cluster with automatic failover
- **Controller Manager**: Multi-replica with leader election
- **Scheduler**: Multi-replica with leader election

#### Application Layer HA

- **API Gateway**: 3+ replicas with load balancing
- **Agent Bus**: 5+ replicas with horizontal scaling
- **Policy Engine**: 3+ replicas with consensus protocol
- **Audit Service**: 3+ replicas with data replication

#### Data Layer HA

- **PostgreSQL**: Aurora Global Database or Patroni cluster
- **Redis**: Redis Cluster with sentinel
- **Kafka**: Multi-broker cluster with replication
- **Object Storage**: Multi-zone replication (S3, GCS, ABS)

## 📋 Prerequisites

### Infrastructure Requirements

#### Compute Resources

```
Production HA Configuration:
- Control Plane: 5 nodes × (8 vCPU, 32GB RAM, 500GB SSD)
- Worker Nodes: 15 nodes × (16 vCPU, 64GB RAM, 1TB SSD)
- Storage Nodes: 9 nodes × (8 vCPU, 32GB RAM, 4TB SSD)
- Load Balancers: 2 × Application Load Balancers
- Network: 10Gbps+ with redundant paths
```

#### Network Requirements

- **DNS**: Global DNS with health checks and failover
- **Load Balancing**: Global and regional load balancers
- **Network Security**: Security groups, network ACLs, WAF
- **VPN/Direct Connect**: Secure connectivity between regions
- **CDN**: Global content delivery for static assets

### Software Dependencies

#### Kubernetes Ecosystem

- **Kubernetes**: v1.28+ with HA control plane
- **etcd**: v3.5+ with clustering
- **CoreDNS**: v1.10+ with HA configuration
- **Ingress Controller**: NGINX or Traefik with HA
- **Service Mesh**: Istio or Linkerd for traffic management

#### Storage & Databases

- **PostgreSQL**: Aurora, Cloud SQL, or Patroni (HA)
- **Redis**: Redis Cluster or AWS ElastiCache
- **Kafka**: Confluent Platform or Amazon MSK
- **Object Storage**: S3, GCS, or Azure Blob with replication

## 🚀 Deployment Process

### Phase 1: Infrastructure Provisioning

#### 1. Multi-Region Networking

```hcl
# Terraform configuration for multi-region VPC
resource "aws_vpc" "acgs2" {
  provider   = aws.primary
  cidr_block = "10.0.0.0/16"

  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "acgs2-ha-vpc"
  }
}

# Transit Gateway for cross-region connectivity
resource "aws_ec2_transit_gateway" "acgs2" {
  description = "ACGS-2 HA transit gateway"

  tags = {
    Name = "acgs2-tgw"
  }
}

# VPN connections for secure cross-region communication
resource "aws_vpn_connection" "acgs2" {
  customer_gateway_id = aws_customer_gateway.acgs2.id
  transit_gateway_id  = aws_ec2_transit_gateway.acgs2.id
  type               = "ipsec.1"

  tags = {
    Name = "acgs2-vpn"
  }
}
```

#### 2. Kubernetes HA Cluster

```bash
# Initialize HA control plane
kubeadm init \
  --control-plane-endpoint "acgs2-control-plane.example.com:6443" \
  --upload-certs \
  --pod-network-cidr "10.244.0.0/16" \
  --service-cidr "10.96.0.0/12"

# Join additional control plane nodes
kubeadm join acgs2-control-plane.example.com:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <key>

# Deploy HA etcd cluster
kubectl apply -f etcd-ha.yaml

# Deploy network plugin with HA
kubectl apply -f calico-ha.yaml
```

#### 3. Load Balancer Configuration

```yaml
# AWS Application Load Balancer with cross-zone
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: acgs2-api
spec:
  serviceRef:
    name: acgs2-api-gateway
    port: 80
  targetGroupARN: arn:aws:elasticloadbalancing:region:account:targetgroup/acgs2-api/123456789
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: acgs2-api-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/success-codes: 200-399
spec:
  rules:
    - host: api.acgs2.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: acgs2-api-gateway
                port:
                  number: 80
```

### Phase 2: Database HA Configuration

#### 1. PostgreSQL HA Setup

```yaml
# PostgreSQL HA with Patroni
apiVersion: postgres-operator.crunchydata.com/v1beta1
kind: PostgresCluster
metadata:
  name: acgs2-postgres
spec:
  image: registry.developers.crunchydata.com/crunchydata/crunchy-postgres:ubi8-15.4-0
  postgresVersion: 15
  instances:
    - name: instance1
      replicas: 3
      dataVolumeClaimSpec:
        accessModes:
          - "ReadWriteOnce"
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 1Ti
    - name: instance2
      replicas: 3
      dataVolumeClaimSpec:
        accessModes:
          - "ReadWriteOnce"
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 1Ti
  backups:
    pgbackrest:
      image: registry.developers.crunchydata.com/crunchydata/crunchy-pgbackrest:ubi8-2.47-0
      repos:
        - name: repo1
          s3:
            bucket: acgs2-postgres-backups
            endpoint: s3.us-east-1.amazonaws.com
            region: us-east-1
        - name: repo2
          s3:
            bucket: acgs2-postgres-backups-dr
            endpoint: s3.us-west-2.amazonaws.com
            region: us-west-2
  proxy:
    pgBouncer:
      image: registry.developers.crunchydata.com/crunchydata/crunchy-pgbouncer:ubi8-1.19-0
      replicas: 3
```

#### 2. Redis HA Cluster

```yaml
# Redis Cluster with HA
apiVersion: redis.redis.opstreelabs.in/v1beta1
kind: RedisCluster
metadata:
  name: acgs2-redis
spec:
  clusterSize: 6
  persistenceEnabled: true
  kubernetesConfig:
    image: quay.io/opstree/redis:v7.0.12
    imagePullPolicy: IfNotPresent
  redisConfig: {}
  storage:
    volumeClaimTemplate:
      spec:
        storageClassName: fast-ssd
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 100Gi
  redisExporter:
    enabled: true
    image: quay.io/opstree/redis-exporter:v1.44.0
```

#### 3. Kafka HA Configuration

```yaml
# Kafka cluster with HA and cross-zone replication
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: acgs2-kafka
spec:
  kafka:
    version: 3.4.0
    replicas: 5
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.min.isr: 2
      transaction.state.log.replication.factor: 3
      default.replication.factor: 3
      min.insync.replicas: 2
    storage:
      type: jbod
      volumes:
        - id: 0
          type: persistent-claim
          size: 1000Gi
          deleteClaim: false
  zookeeper:
    replicas: 3
    storage:
      type: persistent-claim
      size: 100Gi
      deleteClaim: false
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

### Phase 3: Application HA Deployment

#### 1. ACGS-2 Core Services

```yaml
# Enhanced Agent Bus with HA
apiVersion: apps/v1
kind: Deployment
metadata:
  name: acgs2-enhanced-agent-bus
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2
      maxUnavailable: 1
  selector:
    matchLabels:
      app: acgs2-enhanced-agent-bus
  template:
    metadata:
      labels:
        app: acgs2-enhanced-agent-bus
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - acgs2-enhanced-agent-bus
              topologyKey: kubernetes.io/hostname
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values:
                        - acgs2-enhanced-agent-bus
                topologyKey: topology.kubernetes.io/zone
      containers:
        - name: agent-bus
          image: acgs2/enhanced-agent-bus:3.0.0
          resources:
            requests:
              cpu: 1000m
              memory: 2Gi
            limits:
              cpu: 2000m
              memory: 4Gi
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          env:
            - name: POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
            - name: NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: acgs2-enhanced-agent-bus-hpa
spec:
  scaleTargetRef:
    apiGroup: apps
    kind: Deployment
    name: acgs2-enhanced-agent-bus
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
        - type: Pods
          value: 2
          periodSeconds: 60
```

#### 2. Service Mesh Configuration

```yaml
# Istio Service Mesh for traffic management
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: acgs2-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - api.acgs2.com
    - port:
        number: 443
        name: https
        protocol: HTTPS
      tls:
        mode: SIMPLE
        credentialName: acgs2-tls
      hosts:
        - api.acgs2.com
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: acgs2-api
spec:
  hosts:
    - api.acgs2.com
  gateways:
    - acgs2-gateway
  http:
    - match:
        - uri:
            prefix: /api/v1
      route:
        - destination:
            host: acgs2-api-gateway
            port:
              number: 80
      timeout: 30s
      retries:
        attempts: 3
        perTryTimeout: 10s
      fault:
        delay:
          percentage:
            value: 0.1
          fixedDelay: 5s
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: acgs2-api-gateway
spec:
  host: acgs2-api-gateway
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutiveLocalOriginFailures: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

## 🔍 Monitoring & Observability

### HA Monitoring Stack

#### 1. Prometheus HA Configuration

```yaml
# Prometheus HA with Thanos
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: acgs2-prometheus
  namespace: monitoring
spec:
  replicas: 2
  retention: 6h
  ruleSelector:
    matchLabels:
      prometheus: acgs2
  securityContext:
    fsGroup: 2000
    runAsNonRoot: true
    runAsUser: 1000
  serviceAccountName: prometheus
  serviceMonitorSelector:
    matchLabels:
      team: acgs2
  thanos:
    image: quay.io/thanos/thanos:v0.31.0
    objectStorageConfig:
      key: thanos.yaml
      name: thanos-objstore-secret
    resources:
      requests:
        memory: 1Gi
  resources:
    requests:
      memory: 2Gi
  ruleNamespaceSelector:
    matchLabels:
      team: acgs2
```

#### 2. Alert Manager HA

```yaml
# AlertManager HA configuration
apiVersion: monitoring.coreos.com/v1
kind: Alertmanager
metadata:
  name: acgs2-alertmanager
  namespace: monitoring
spec:
  replicas: 3
  forceEnableClusterMode: true
  configSecret: alertmanager-config
  resources:
    requests:
      memory: 1Gi
  securityContext:
    fsGroup: 2000
    runAsNonRoot: true
    runAsUser: 1000
  serviceAccountName: alertmanager
```

#### 3. Distributed Tracing

```yaml
# Jaeger with Elasticsearch storage
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: acgs2-jaeger
spec:
  strategy: production
  storage:
    type: elasticsearch
    esIndexCleaner:
      enabled: true
      numberOfDays: 7
      schedule: "55 23 * * *"
    esRollover:
      conditions: '{"max_age": "2d"}'
      readTTL: "7d"
  ingress:
    enabled: true
    hosts:
      - jaeger.acgs2.com
  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 1000m
```

### SLA Monitoring

#### 1. Service Level Objectives

```yaml
# SLO monitoring with SLIs
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: acgs2-slo-rules
  namespace: monitoring
spec:
  groups:
    - name: acgs2-slo
      rules:
        # API Availability SLO
        - alert: APISLOViolation
          expr: |
            1 - (sum(rate(http_requests_total{status=~"5.."}[30d])) by (service))
            / sum(rate(http_requests_total[30d])) by (service) < 0.9999
          for: 5m
          labels:
            severity: critical
            slo: api-availability
          annotations:
            summary: "API Availability SLO violation"
            description: "API availability has dropped below 99.99%"

        # Latency SLO
        - alert: LatencySLOViolation
          expr: |
            histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[30d]))
            > 5
          for: 5m
          labels:
            severity: warning
            slo: api-latency
          annotations:
            summary: "API Latency SLO violation"
            description: "P99 latency has exceeded 5 seconds"
```

## 🔄 Backup & Disaster Recovery

### Multi-Region Backup Strategy

#### 1. Database Backup

```bash
# Multi-region PostgreSQL backup
pg_dump --host=acgs2-postgres-primary --username=acgs2 --format=custom \
  --compress=9 --verbose --file=/backups/$(date +%Y%m%d_%H%M%S)_acgs2.dump \
  acgs2

# Cross-region replication
aws s3 cp /backups/*.dump s3://acgs2-backups-us-east-1/ --recursive
aws s3 cp /backups/*.dump s3://acgs2-backups-us-west-2/ --recursive
```

#### 2. Application State Backup

```yaml
# Velero for Kubernetes backup
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: acgs2-daily-backup
  namespace: velero
spec:
  includedNamespaces:
    - acgs2-system
    - acgs2-monitoring
    - acgs2-security
  storageLocation: aws-s3-backup
  ttl: 720h0m0s
  schedule: "0 2 * * *"
```

#### 3. Disaster Recovery Testing

```bash
#!/bin/bash
# acgs2-dr-test.sh

echo "Starting ACGS-2 Disaster Recovery Test..."

# 1. Simulate region failure
kubectl delete node $(kubectl get nodes -l topology.kubernetes.io/region=us-east-1 -o jsonpath='{.items[*].metadata.name}')

# 2. Verify failover
kubectl wait --for=condition=ready pod -l app=acgs2-enhanced-agent-bus --timeout=300s

# 3. Test application functionality
curl -f https://api.acgs2.com/health || exit 1

# 4. Verify data consistency
kubectl exec -it deployment/acgs2-postgres-replica -- psql -c "SELECT count(*) FROM policies;"

echo "Disaster Recovery Test Completed Successfully"
```

## 🚨 Incident Response

### Automated Failover Procedures

#### 1. Node Failure Response

```yaml
# Automatic pod rescheduling on node failure
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: acgs2-critical-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: acgs2-enhanced-agent-bus
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: acgs2-failover-controller
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: failover-controller
          image: acgs2/failover-controller:3.0.0
          env:
            - name: KUBECONFIG
              value: /etc/kubernetes/admin.conf
          volumeMounts:
            - name: kubeconfig
              mountPath: /etc/kubernetes
      volumes:
        - name: kubeconfig
          secret:
            secretName: kubeconfig
```

#### 2. Regional Failover

```bash
#!/bin/bash
# acgs2-regional-failover.sh

PRIMARY_REGION="us-east-1"
SECONDARY_REGION="us-west-2"

echo "Initiating regional failover from $PRIMARY_REGION to $SECONDARY_REGION..."

# 1. Update DNS to point to secondary region
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file://dns-failover.json

# 2. Promote secondary database
aws rds failover-db-cluster \
  --db-cluster-identifier acgs2-postgres \
  --target-db-instance-identifier acgs2-postgres-secondary

# 3. Scale up secondary region
kubectl config use-context $SECONDARY_REGION
kubectl scale deployment acgs2-enhanced-agent-bus --replicas=8

# 4. Verify failover completion
curl -f https://api.acgs2.com/health || exit 1

echo "Regional failover completed successfully"
```

### Incident Management

#### 1. Alert Classification

```yaml
# Alert severity classification
alerts:
  critical:
    - "APISLOViolation"
    - "DatabaseDown"
    - "ControlPlaneUnhealthy"
    - "SecurityBreach"
  warning:
    - "HighLatency"
    - "ResourceExhaustion"
    - "BackupFailure"
  info:
    - "MaintenanceWindow"
    - "ConfigurationChange"
```

#### 2. Escalation Procedures

```yaml
# Incident response escalation
escalation:
  immediate:
    - "Page on-call SRE"
    - "Notify incident commander"
  15_minutes:
    - "Escalate to engineering manager"
    - "Notify customer success"
  1_hour:
    - "Escalate to VP of Engineering"
    - "Notify executive team"
  4_hours:
    - "Escalate to CEO"
    - "Prepare public communication"
```

## 📊 Performance Optimization

### Auto-Scaling Configuration

#### 1. Horizontal Pod Autoscaler

```yaml
# Advanced HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: acgs2-api-gateway-hpa
spec:
  scaleTargetRef:
    apiGroup: apps
    kind: Deployment
    name: acgs2-api-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: 100
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
        - type: Pods
          value: 1
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
        - type: Pods
          value: 4
          periodSeconds: 60
```

#### 2. Cluster Autoscaler

```yaml
# Cluster autoscaler for node scaling
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  template:
    spec:
      containers:
        - name: cluster-autoscaler
          image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.27.0
          command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/acgs2
            - --balance-similar-node-groups
            - --skip-nodes-with-system-pods=false
          env:
            - name: AWS_REGION
              value: us-east-1
```

### Capacity Planning

#### 1. Resource Monitoring

```yaml
# Resource capacity monitoring
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: acgs2-capacity-alerts
spec:
  groups:
    - name: capacity
      rules:
        - alert: NodeCPUHigh
          expr: (1 - rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 90
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High CPU usage on node"
            description: "CPU usage is above 90% for more than 10 minutes"

        - alert: NodeMemoryHigh
          expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High memory usage on node"
            description: "Memory usage is above 90% for more than 10 minutes"
```

## 🔒 Security Hardening

### Network Security

#### 1. Network Policies

```yaml
# Comprehensive network policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: acgs2-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: acgs2-allow-internal
spec:
  podSelector:
    matchLabels:
      acgs2/tenant-id: acgs2-main
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              acgs2/tenant-id: acgs2-main
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
  egress:
    - to:
        - podSelector:
            matchLabels:
              acgs2/tenant-id: acgs2-main
        - namespaceSelector:
            matchLabels:
              name: kube-system
    - to: []
      ports:
        - protocol: TCP
          port: 443
        - protocol: TCP
          port: 53
        - protocol: UDP
          port: 53
```

#### 2. Security Contexts

```yaml
# Hardened security contexts
apiVersion: apps/v1
kind: Deployment
metadata:
  name: acgs2-enhanced-agent-bus
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
        - name: agent-bus
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 1000
          resources:
            requests:
              cpu: 1000m
              memory: 2Gi
            limits:
              cpu: 2000m
              memory: 4Gi
```

---

## 📋 HA Deployment Checklist

### Infrastructure

- [ ] Multi-region VPCs configured
- [ ] Transit Gateway/VPN for cross-region connectivity
- [ ] Global load balancers deployed
- [ ] DNS failover configuration tested
- [ ] CDN for static asset delivery

### Kubernetes

- [ ] HA control plane (3+ masters)
- [ ] etcd clustering configured
- [ ] Network plugin with cross-subnet support
- [ ] Ingress controllers in multiple zones
- [ ] Service mesh for traffic management

### Databases

- [ ] PostgreSQL HA with synchronous replication
- [ ] Redis cluster with sentinel
- [ ] Kafka with multi-broker replication
- [ ] Object storage with cross-region replication
- [ ] Backup automation configured

### Applications

- [ ] ACGS-2 services deployed with anti-affinity
- [ ] Horizontal Pod Autoscalers configured
- [ ] Pod Disruption Budgets set
- [ ] Health checks and readiness probes
- [ ] Rolling update strategies defined

### Monitoring

- [ ] Prometheus HA with Thanos
- [ ] Alert Manager with clustering
- [ ] Distributed tracing (Jaeger)
- [ ] SLO monitoring and alerting
- [ ] Log aggregation with retention

### Security

- [ ] Network policies enforced
- [ ] Security contexts hardened
- [ ] Service mesh with mTLS
- [ ] WAF and DDoS protection
- [ ] Encryption at rest and in transit

### Backup & Recovery

- [ ] Multi-region backup strategy
- [ ] Automated backup verification
- [ ] Disaster recovery procedures documented
- [ ] Failover testing completed
- [ ] RTO/RPO objectives validated

### Testing

- [ ] Load testing completed
- [ ] Chaos engineering experiments run
- [ ] Failover procedures tested
- [ ] Performance benchmarks established
- [ ] Security penetration testing passed

---

**🎯 Key Success Metrics:**

1. **Availability**: Achieve 99.99% uptime
2. **Recovery**: RTO < 5 minutes, RPO < 1 minute
3. **Performance**: P99 latency < 5ms
4. **Security**: Zero security incidents
5. **Compliance**: All frameworks satisfied

For enterprise HA deployments requiring custom configurations or additional features, contact the ACGS-2 Enterprise Solutions team.
