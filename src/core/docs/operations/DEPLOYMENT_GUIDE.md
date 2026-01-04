# ACGS-2 Enterprise Deployment Guide

> **Constitutional Hash**: `cdd01ef066bc6cf2` > **Version**: 2.1.0
> **Status**: Stable
> **Last Updated**: 2025-12-20
> **Language**: EN

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [AWS Deployment](#aws-deployment)
4. [GCP Deployment](#gcp-deployment)
5. [Helm Chart Deployment](#helm-chart-deployment)
6. [Identity Provider Integration](#identity-provider-integration)
7. [Post-Deployment Configuration](#post-deployment-configuration)
8. [Monitoring & Observability](#monitoring--observability)
9. [Security Hardening](#security-hardening)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

| Tool       | Version   | Purpose                     |
| ---------- | --------- | --------------------------- |
| Terraform  | >= 1.6.0  | Infrastructure provisioning |
| Helm       | >= 3.13.0 | Kubernetes deployment       |
| kubectl    | >= 1.28   | Kubernetes management       |
| AWS CLI    | >= 2.0    | AWS operations              |
| gcloud CLI | >= 450.0  | GCP operations              |

### Access Requirements

**AWS:**

- IAM user/role with administrative permissions
- Access to create EKS, RDS, ElastiCache, MSK, ECR resources
- Route53 hosted zone (for DNS)

**GCP:**

- Service account with Owner or specific IAM roles
- Access to create GKE, Cloud SQL, Memorystore, Pub/Sub resources
- Cloud DNS zone (for DNS)

### Network Requirements

| Port | Protocol | Purpose                   |
| ---- | -------- | ------------------------- |
| 443  | HTTPS    | API Gateway, Web UI       |
| 5432 | TCP      | PostgreSQL                |
| 6379 | TCP      | Redis                     |
| 9092 | TCP      | Kafka                     |
| 8001 | TCP      | Constitutional AI Service |
| 8010 | TCP      | API Gateway (internal)    |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
│                     (ALB/Cloud Load Balancer)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Kubernetes Cluster                            │
│                     (EKS / GKE Autopilot)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ API Gateway │  │Constitutional│  │ Agent Bus   │              │
│  │   Service   │  │  AI Service │  │   Service   │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│  ┌──────▼────────────────▼────────────────▼──────┐              │
│  │              Internal Service Mesh             │              │
│  └────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌───────▼───────┐  ┌───────▼───────┐
│  PostgreSQL   │  │    Redis      │  │    Kafka      │
│ (RDS/CloudSQL)│  │(ElastiCache/  │  │ (MSK/Pub-Sub) │
│               │  │  Memorystore) │  │               │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## AWS Deployment

### Step 1: Configure Backend

Create an S3 bucket for Terraform state:

```bash
aws s3 mb s3://acgs2-terraform-state-${AWS_ACCOUNT_ID} --region us-east-1

aws s3api put-bucket-versioning \
  --bucket acgs2-terraform-state-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name acgs2-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### Step 2: Configure Variables

Create `deploy/terraform/aws/environments/production.tfvars`:

```hcl
# Project Configuration
project_name = "acgs2"
environment  = "production"
aws_region   = "us-east-1"

# Networking
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["us-east-1a", "us-east-1b", "us-east-1c"]
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# EKS Configuration
eks_cluster_version = "1.28"
eks_node_groups = {
  general = {
    instance_types = ["m6i.xlarge"]
    min_size       = 3
    max_size       = 10
    desired_size   = 3
    disk_size      = 100
    labels = {
      role = "general"
    }
  }
  compute = {
    instance_types = ["c6i.2xlarge"]
    min_size       = 2
    max_size       = 20
    desired_size   = 2
    disk_size      = 100
    labels = {
      role = "compute"
    }
    taints = [{
      key    = "dedicated"
      value  = "compute"
      effect = "NO_SCHEDULE"
    }]
  }
}

# RDS Configuration
rds_instance_class         = "db.r6g.xlarge"
rds_allocated_storage      = 100
rds_max_allocated_storage  = 500
rds_multi_az               = true
rds_backup_retention_period = 30
rds_deletion_protection    = true

# ElastiCache Configuration
elasticache_node_type       = "cache.r6g.large"
elasticache_num_cache_nodes = 3
elasticache_automatic_failover = true

# MSK Configuration
msk_instance_type   = "kafka.m5.large"
msk_number_of_nodes = 3
msk_ebs_volume_size = 100

# Tags
tags = {
  Project              = "ACGS-2"
  Environment          = "production"
  ConstitutionalHash   = "cdd01ef066bc6cf2"
  ManagedBy            = "terraform"
}
```

### Step 3: Deploy Infrastructure

```bash
cd deploy/terraform/aws

# Initialize Terraform
terraform init \
  -backend-config="bucket=acgs2-terraform-state-${AWS_ACCOUNT_ID}" \
  -backend-config="key=acgs2/production/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=acgs2-terraform-locks"

# Review plan
terraform plan -var-file="environments/production.tfvars" -out=tfplan

# Apply infrastructure
terraform apply tfplan
```

### Step 4: Configure kubectl

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name acgs2-production \
  --alias acgs2-production
```

---

## GCP Deployment

### Step 1: Configure Backend

```bash
# Create GCS bucket for state
gsutil mb -p ${GCP_PROJECT_ID} -l us-central1 gs://acgs2-terraform-state-${GCP_PROJECT_ID}
gsutil versioning set on gs://acgs2-terraform-state-${GCP_PROJECT_ID}
```

### Step 2: Configure Variables

Create `deploy/terraform/gcp/environments/production.tfvars`:

```hcl
# Project Configuration
project_id  = "your-gcp-project-id"
region      = "us-central1"
environment = "production"

# GKE Configuration
gke_enable_autopilot = true
gke_release_channel  = "STABLE"

# Cloud SQL Configuration
cloudsql_tier                = "db-custom-4-16384"
cloudsql_availability_type   = "REGIONAL"
cloudsql_disk_size           = 100
cloudsql_backup_enabled      = true
cloudsql_point_in_time_recovery = true

# Memorystore Configuration
memorystore_tier          = "STANDARD_HA"
memorystore_memory_size   = 5
memorystore_replica_count = 2

# Labels
labels = {
  project            = "acgs2"
  environment        = "production"
  constitutional-hash = "cdd01ef066bc6cf2"
  managed-by         = "terraform"
}
```

### Step 3: Deploy Infrastructure

```bash
cd deploy/terraform/gcp

terraform init \
  -backend-config="bucket=acgs2-terraform-state-${GCP_PROJECT_ID}" \
  -backend-config="prefix=acgs2/production"

terraform plan -var-file="environments/production.tfvars" -out=tfplan

terraform apply tfplan
```

### Step 4: Configure kubectl

```bash
gcloud container clusters get-credentials acgs2-production \
  --region us-central1 \
  --project ${GCP_PROJECT_ID}
```

---

## Helm Chart Deployment

### Step 1: Add Helm Repository

```bash
# Add required repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Step 2: Configure Values

Create `values-production.yaml`:

```yaml
global:
  environment: production
  constitutionalHash: "cdd01ef066bc6cf2"

# API Gateway
apiGateway:
  replicaCount: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi
  ingress:
    enabled: true
    className: nginx
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt-prod
    hosts:
      - host: api.acgs.yourdomain.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: acgs2-api-tls
        hosts:
          - api.acgs.yourdomain.com

# Constitutional Service
constitutionalService:
  replicaCount: 3
  resources:
    requests:
      cpu: 1000m
      memory: 2Gi
    limits:
      cpu: 4000m
      memory: 8Gi

# Agent Bus
agentBus:
  replicaCount: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

# External Services (use Terraform-provisioned)
postgresql:
  enabled: false
externalDatabase:
  host: "your-rds-endpoint.rds.amazonaws.com"
  port: 5432
  database: acgs2
  existingSecret: acgs2-db-credentials

redis:
  enabled: false
externalRedis:
  host: "your-elasticache-endpoint.cache.amazonaws.com"
  port: 6379
  existingSecret: acgs2-redis-credentials

kafka:
  enabled: false
externalKafka:
  brokers: "your-msk-brokers:9092"
  existingSecret: acgs2-kafka-credentials

# Monitoring
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
```

### Step 3: Create Secrets

```bash
# Database credentials
kubectl create secret generic acgs2-db-credentials \
  --from-literal=username=acgs2_admin \
  --from-literal=password='your-secure-password' \
  -n acgs2

# Redis credentials
kubectl create secret generic acgs2-redis-credentials \
  --from-literal=password='your-redis-password' \
  -n acgs2

# API keys
kubectl create secret generic acgs2-api-keys \
  --from-literal=jwt-secret='your-jwt-secret' \
  --from-literal=encryption-key='your-encryption-key' \
  -n acgs2
```

### Step 4: Deploy

```bash
# Create namespace
kubectl create namespace acgs2

# Install chart
helm upgrade --install acgs2 ./deploy/helm/acgs2 \
  --namespace acgs2 \
  --values values-production.yaml \
  --wait \
  --timeout 10m
```

---

## Identity Provider Integration

### Okta Configuration

1. Create an Okta application:

   - Application type: OIDC - Web Application
   - Grant types: Authorization Code, Refresh Token
   - Sign-in redirect URIs: `https://api.acgs.yourdomain.com/auth/okta/callback`

2. Configure ACGS-2:

```yaml
# In Helm values
identity:
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "your-client-id"
    existingSecret: acgs2-okta-credentials
    groupMapping:
      "ACGS-Admins": "admin"
      "ACGS-Operators": "operator"
      "ACGS-Viewers": "viewer"
```

### Azure AD Configuration

1. Register an application in Azure AD:

   - Supported account types: Single tenant
   - Redirect URI: `https://api.acgs.yourdomain.com/auth/azure/callback`

2. Configure ACGS-2:

```yaml
identity:
  azureAd:
    enabled: true
    tenantId: "your-tenant-id"
    clientId: "your-client-id"
    existingSecret: acgs2-azure-credentials
```

---

## Post-Deployment Configuration

### Verify Deployment

```bash
# Check pod status
kubectl get pods -n acgs2

# Check services
kubectl get svc -n acgs2

# Verify constitutional hash in logs
kubectl logs -n acgs2 -l app.kubernetes.io/name=constitutional-service | grep "cdd01ef066bc6cf2"
```

### Initialize System

```bash
# Run database migrations
kubectl exec -n acgs2 deployment/acgs2-api-gateway -- python manage.py migrate

# Create initial admin user
kubectl exec -n acgs2 deployment/acgs2-api-gateway -- python manage.py createsuperuser
```

### Health Check

```bash
# API health
curl https://api.acgs.yourdomain.com/health

# Constitutional service health
curl https://api.acgs.yourdomain.com/api/v1/constitutional/health
```

---

## Monitoring & Observability

### Prometheus/Grafana

The Helm chart includes ServiceMonitor and PrometheusRule resources:

```bash
# Verify ServiceMonitor
kubectl get servicemonitor -n acgs2

# Access Grafana dashboards
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
```

### Key Metrics

| Metric                            | Description                    | Alert Threshold |
| --------------------------------- | ------------------------------ | --------------- |
| `acgs2_constitutional_hash_valid` | Constitutional hash validation | != 1            |
| `acgs2_request_duration_seconds`  | Request latency                | P99 > 5s        |
| `acgs2_compliance_check_total`    | Compliance validations         | Error rate > 1% |
| `acgs2_agent_messages_total`      | Agent message throughput       | -               |

---

## Production Sizing Guide

To ensure optimal performance and reliability of the ACGS-2 platform, follow these hardware recommendations based on your expected workload.

### Deployment Tiers

| Component      | Small (Dev/Test) | Medium (Staging)    | Large (Production) |
| -------------- | ---------------- | ------------------- | ------------------ |
| **Throughput** | < 100 msg/sec    | 100 - 1,000 msg/sec | > 1,000 msg/sec    |
| **Agents**     | < 50             | 50 - 500            | > 500              |

### Resource Recommendations (Per Replica)

#### API Gateway

- **Small**: 0.5 vCPU, 512Mi RAM
- **Medium**: 1 vCPU, 1Gi RAM
- **Large**: 2 vCPU, 2Gi RAM

#### Constitutional Service

- **Small**: 1 vCPU, 2Gi RAM
- **Medium**: 2 vCPU, 4Gi RAM
- **Large**: 4 vCPU, 8Gi RAM

#### Agent Bus Service

- **Small**: 0.5 vCPU, 1Gi RAM
- **Medium**: 1 vCPU, 2Gi RAM
- **Large**: 2 vCPU, 4Gi RAM

#### Deliberation Layer (BERT)

- **Small**: 1 vCPU, 2Gi RAM
- **Medium**: 2 vCPU, 4Gi RAM
- **Large**: 4 vCPU, 8Gi RAM (GPU recommended)

### Infrastructure Services

| Service        | Small          | Medium          | Large            |
| -------------- | -------------- | --------------- | ---------------- |
| **PostgreSQL** | db.t3.medium   | db.m6g.large    | db.r6g.xlarge    |
| **Redis**      | cache.t3.small | cache.m6g.large | cache.r6g.large  |
| **Kafka**      | kafka.t3.small | kafka.m5.large  | kafka.m5.2xlarge |

### Storage Recommendations

- **Audit Logs**: 100GB+ (SSD recommended)
- **Message Queue**: 50GB+ (High IOPS)
- **Policy Registry**: 10GB+

---

## Security Hardening

### Network Policies

The deployment includes zero-trust network policies. Verify:

```bash
kubectl get networkpolicy -n acgs2
```

### Pod Security

All pods run with:

- Non-root user (UID 1000)
- Read-only root filesystem
- Dropped capabilities
- Seccomp profile

### Secrets Management

For production, consider:

- AWS Secrets Manager / GCP Secret Manager integration
- HashiCorp Vault for dynamic secrets
- Sealed Secrets for GitOps workflows

---

## Troubleshooting

### Common Issues

**Pod CrashLoopBackOff:**

```bash
kubectl describe pod -n acgs2 <pod-name>
kubectl logs -n acgs2 <pod-name> --previous
```

**Database Connection Issues:**

```bash
# Test connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h <db-host> -U acgs2_admin -d acgs2
```

**Constitutional Hash Mismatch:**

```bash
# Check all services for hash consistency
kubectl exec -n acgs2 deployment/acgs2-constitutional-service -- \
  grep -r "cdd01ef066bc6cf2" /app/
```

### Support

- Documentation: https://docs.acgs.io
- Issues: https://github.com/acgs/acgs2/issues
- Email: support@acgs.io

---

**Constitutional Hash:** `cdd01ef066bc6cf2` - All deployments must validate against this hash.
