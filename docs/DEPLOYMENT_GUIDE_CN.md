# ACGS-2 企业级部署指南

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Version**: 2.1.0
> **Status**: Stable
> **Last Updated**: 2025-12-20
> **Language**: CN

本文档涵盖了使用提供的 Terraform 模块和 Helm 部署包将 ACGS-2（AI 宪法治理系统）部署到 AWS 和 GCP 生产环境的详细说明。

## 目录

1. [前置条件](#前置条件)
2. [架构概览](#架构概览)
3. [AWS 部署](#aws-部署)
4. [GCP 部署](#gcp-部署)
5. [Helm Chart 部署](#helm-chart-部署)
6. [身份提供商集成](#身份提供商集成)
7. [部署后配置](#部署后配置)
8. [监控与可观测性](#监控与可观测性)
9. [安全加固](#安全加固)
10. [故障排除](#故障排除)

---

## 前置条件

### 核心工具

| 工具 | 版本 | 用途 |
|------|---------|---------|
| Terraform | >= 1.6.0 | 基础设施置备 |
| Helm | >= 3.13.0 | Kubernetes 部署 |
| kubectl | >= 1.28 | Kubernetes 管理 |
| AWS CLI | >= 2.0 | AWS 操作 |
| gcloud CLI | >= 450.0 | GCP 操作 |

### 访问权限要求

**AWS:**
- 具有管理权限的 IAM 用户/角色
- 创建 EKS, RDS, ElastiCache, MSK, ECR 资源的权限
- Route53 托管区域（用于 DNS）

**GCP:**
- 具有 Owner 或特定 IAM 角色的服务帐号
- 创建 GKE, Cloud SQL, Memorystore, Pub/Sub 资源的权限
- Cloud DNS 区域（用于 DNS）

### 网络要求

| 端口 | 协议 | 用途 |
|------|----------|---------|
| 443 | HTTPS | API 网关, Web UI |
| 5432 | TCP | PostgreSQL |
| 6379 | TCP | Redis |
| 9092 | TCP | Kafka |
| 8001 | TCP | 宪法 AI 服务 (Constitutional AI Service) |
| 8010 | TCP | API 网关 (内部) |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        负载均衡器                               │
│                     (ALB/Cloud Load Balancer)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Kubernetes 集群                              │
│                     (EKS / GKE Autopilot)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ API 网关    │  │   宪法 AI   │  │  代理总线   │              │
│  │    服务     │  │    服务     │  │    服务     │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│  ┌──────▼────────────────▼────────────────▼──────┐              │
│  │              内部服务网格 (Service Mesh)       │              │
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

## AWS 部署

### 步骤 1: 配置后端

为 Terraform 状态创建一个 S3 存储桶：

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

### 步骤 2: 配置变量

创建 `deploy/terraform/aws/environments/production.tfvars`:

```hcl
# 项目配置
project_name = "acgs2"
environment  = "production"
aws_region   = "us-east-1"

# 网络配置
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["us-east-1a", "us-east-1b", "us-east-1c"]
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# EKS 配置
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

# RDS 配置
rds_instance_class         = "db.r6g.xlarge"
rds_allocated_storage      = 100
rds_max_allocated_storage  = 500
rds_multi_az               = true
rds_backup_retention_period = 30
rds_deletion_protection    = true

# ElastiCache 配置
elasticache_node_type       = "cache.r6g.large"
elasticache_num_cache_nodes = 3
elasticache_automatic_failover = true

# MSK 配置
msk_instance_type   = "kafka.m5.large"
msk_number_of_nodes = 3
msk_ebs_volume_size = 100

# 标签
tags = {
  Project              = "ACGS-2"
  Environment          = "production"
  ConstitutionalHash   = "cdd01ef066bc6cf2"
  ManagedBy            = "terraform"
}
```

### 步骤 3: 部署基础设施

```bash
cd deploy/terraform/aws

# 初始化 Terraform
terraform init \
  -backend-config="bucket=acgs2-terraform-state-${AWS_ACCOUNT_ID}" \
  -backend-config="key=acgs2/production/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=acgs2-terraform-locks"

# 审查计划
terraform plan -var-file="environments/production.tfvars" -out=tfplan

# 应用基础设施
terraform apply tfplan
```

### 步骤 4: 配置 kubectl

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name acgs2-production \
  --alias acgs2-production
```

---

## GCP 部署

### 步骤 1: 配置后端

```bash
# 创建用于状态存储的 GCS 存储桶
gsutil mb -p ${GCP_PROJECT_ID} -l us-central1 gs://acgs2-terraform-state-${GCP_PROJECT_ID}
gsutil versioning set on gs://acgs2-terraform-state-${GCP_PROJECT_ID}
```

### 步骤 2: 配置变量

创建 `deploy/terraform/gcp/environments/production.tfvars`:

```hcl
# 项目配置
project_id  = "your-gcp-project-id"
region      = "us-central1"
environment = "production"

# GKE 配置
gke_enable_autopilot = true
gke_release_channel  = "STABLE"

# Cloud SQL 配置
cloudsql_tier                = "db-custom-4-16384"
cloudsql_availability_type   = "REGIONAL"
cloudsql_disk_size           = 100
cloudsql_backup_enabled      = true
cloudsql_point_in_time_recovery = true

# Memorystore 配置
memorystore_tier          = "STANDARD_HA"
memorystore_memory_size   = 5
memorystore_replica_count = 2

# 标签
labels = {
  project            = "acgs2"
  environment        = "production"
  constitutional-hash = "cdd01ef066bc6cf2"
  managed-by         = "terraform"
}
```

### 步骤 3: 部署基础设施

```bash
cd deploy/terraform/gcp

terraform init \
  -backend-config="bucket=acgs2-terraform-state-${GCP_PROJECT_ID}" \
  -backend-config="prefix=acgs2/production"

terraform plan -var-file="environments/production.tfvars" -out=tfplan

terraform apply tfplan
```

### 步骤 4: 配置 kubectl

```bash
gcloud container clusters get-credentials acgs2-production \
  --region us-central1 \
  --project ${GCP_PROJECT_ID}
```

---

## Helm Chart 部署

### 步骤 1: 添加 Helm 仓库

```bash
# 添加必要的仓库
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 步骤 2: 配置 Values

创建 `values-production.yaml`:

```yaml
global:
  environment: production
  constitutionalHash: "cdd01ef066bc6cf2"

# API 网关
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

# 宪法 AI 服务
constitutionalService:
  replicaCount: 3
  resources:
    requests:
      cpu: 1000m
      memory: 2Gi
    limits:
      cpu: 4000m
      memory: 8Gi

# 代理总线 (Agent Bus)
agentBus:
  replicaCount: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

# 外部服务 (使用 Terraform 置备的)
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

# 监控
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
```

### 步骤 3: 创建 Secrets

```bash
# 数据库凭据
kubectl create secret generic acgs2-db-credentials \
  --from-literal=username=acgs2_admin \
  --from-literal=password='your-secure-password' \
  -n acgs2

# Redis 凭据
kubectl create secret generic acgs2-redis-credentials \
  --from-literal=password='your-redis-password' \
  -n acgs2

# API 密钥
kubectl create secret generic acgs2-api-keys \
  --from-literal=jwt-secret='your-jwt-secret' \
  --from-literal=encryption-key='your-encryption-key' \
  -n acgs2
```

### 步骤 4: 部署

```bash
# 创建命名空间
kubectl create namespace acgs2

# 安装 Chart
helm upgrade --install acgs2 ./deploy/helm/acgs2 \
  --namespace acgs2 \
  --values values-production.yaml \
  --wait \
  --timeout 10m
```

---

## 身份提供商集成

### Okta 配置

1. 创建 Okta 应用:
   - 应用类型: OIDC - Web Application
   - 授权类型: Authorization Code, Refresh Token
   - 登录重定向 URI: `https://api.acgs.yourdomain.com/auth/okta/callback`

2. 配置 ACGS-2:

```yaml
# 在 Helm values 中配置
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

### Azure AD 配置

1. 在 Azure AD 中注册应用:
   - 支持的账户类型: 仅限单租户 (Single tenant)
   - 重定向 URI: `https://api.acgs.yourdomain.com/auth/azure/callback`

2. 配置 ACGS-2:

```yaml
identity:
  azureAd:
    enabled: true
    tenantId: "your-tenant-id"
    clientId: "your-client-id"
    existingSecret: acgs2-azure-credentials
```

---

## 部署后配置

### 验证部署

```bash
# 检查 Pod 状态
kubectl get pods -n acgs2

# 检查服务
kubectl get svc -n acgs2

# 在日志中验证宪法哈希
kubectl logs -n acgs2 -l app.kubernetes.io/name=constitutional-service | grep "cdd01ef066bc6cf2"
```

### 初始化系统

```bash
# 运行数据库迁移
kubectl exec -n acgs2 deployment/acgs2-api-gateway -- python manage.py migrate

# 创建初始管理员用户
kubectl exec -n acgs2 deployment/acgs2-api-gateway -- python manage.py createsuperuser
```

### 健康检查

```bash
# API 健康状态
curl https://api.acgs.yourdomain.com/health

# 宪法服务健康状态
curl https://api.acgs.yourdomain.com/api/v1/constitutional/health
```

---

## 监控与可观测性

### Prometheus/Grafana

Helm Chart 包含了 ServiceMonitor 和 PrometheusRule 资源：

```bash
# 验证 ServiceMonitor
kubectl get servicemonitor -n acgs2

# 访问 Grafana 面板
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
```

### 关键指标

| 指标 | 描述 | 告警阈值 |
|--------|-------------|-----------------|
| `acgs2_constitutional_hash_valid` | 宪法哈希验证状态 | != 1 |
| `acgs2_request_duration_seconds` | 请求延迟 | P99 > 5s |
| `acgs2_compliance_check_total` | 合规性验证 | 错误率 > 1% |
| `acgs2_agent_messages_total` | 代理消息吞吐量 | - |

---

## 安全加固

### 网络策略 (Network Policies)

部署包含零信任网络策略。验证：

```bash
kubectl get networkpolicy -n acgs2
```

### Pod 安全

所有 Pod 运行配置：
- 非 root 用户 (UID 1000)
- 只读根文件系统 (Read-only root filesystem)
- 移除不必要的 capabilities
- 启用 Seccomp profile

### 密钥管理 (Secrets Management)

生产环境建议：
- 集成 AWS Secrets Manager / GCP Secret Manager
- 使用 HashiCorp Vault 进行动态密钥管理
- GitOps 工作流中使用 Sealed Secrets

---

## 故障排除

### 常见问题

**Pod 处于 CrashLoopBackOff 状态:**
```bash
kubectl describe pod -n acgs2 <pod-name>
kubectl logs -n acgs2 <pod-name> --previous
```

**数据库连接问题:**
```bash
# 测试连通性
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h <db-host> -U acgs2_admin -d acgs2
```

**宪法哈希不匹配 (Constitutional Hash Mismatch):**
```bash
# 检查所有服务的哈希一致性
kubectl exec -n acgs2 deployment/acgs2-constitutional-service -- \
  grep -r "cdd01ef066bc6cf2" /app/
```

### 支持

- 文档: https://docs.acgs.io
- 问题反馈: https://github.com/acgs/acgs2/issues
- 邮件: support@acgs.io

---

**Constitutional Hash**: `cdd01ef066bc6cf2` - 所有部署必须针对此哈希进行验证。
