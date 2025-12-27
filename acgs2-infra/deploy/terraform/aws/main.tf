# ACGS-2 AWS Infrastructure
# Constitutional Hash: cdd01ef066bc6cf2
#
# This Terraform configuration deploys ACGS-2 on AWS with:
# - EKS cluster for Kubernetes workloads
# - RDS PostgreSQL for persistent storage
# - ElastiCache Redis for caching
# - MSK (Managed Streaming for Apache Kafka) for event streaming
# - ECR for container registry
# - VPC with multi-AZ networking

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  backend "s3" {
    # Configure in terraform.tfvars or via CLI
    # bucket         = "acgs2-terraform-state"
    # key            = "aws/terraform.tfstate"
    # region         = "us-west-2"
    # encrypt        = true
    # dynamodb_table = "acgs2-terraform-locks"
  }
}

# Local values
locals {
  constitutional_hash = "cdd01ef066bc6cf2"

  common_tags = {
    Project             = "ACGS-2"
    Environment         = var.environment
    ManagedBy           = "Terraform"
    ConstitutionalHash  = local.constitutional_hash
    CostCenter          = var.cost_center
    Owner               = var.owner
  }

  name_prefix = "acgs2-${var.environment}"
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway     = true
  single_nat_gateway     = var.environment != "production"
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_max_aggregation_interval    = 60

  tags = local.common_tags

  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = 1
    "kubernetes.io/cluster/${local.name_prefix}" = "owned"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = 1
    "kubernetes.io/cluster/${local.name_prefix}" = "owned"
  }
}

# EKS Cluster
module "eks" {
  source = "./modules/eks"

  cluster_name    = local.name_prefix
  cluster_version = var.eks_cluster_version

  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  # Node groups
  node_groups = var.eks_node_groups

  # Add-ons
  enable_cluster_autoscaler    = true
  enable_metrics_server        = true
  enable_aws_load_balancer     = true
  enable_external_secrets      = true
  enable_cert_manager          = true

  # OIDC
  enable_irsa = true

  tags = local.common_tags
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"

  identifier = "${local.name_prefix}-db"

  engine_version    = var.rds_engine_version
  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage

  database_name = "acgs"
  username      = "acgs_admin"

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  security_group_ids = [module.eks.cluster_security_group_id]

  # High availability
  multi_az = var.environment == "production"

  # Backup
  backup_retention_period = var.rds_backup_retention
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  # Encryption
  storage_encrypted = true
  kms_key_id       = module.kms.key_arn

  # Performance Insights
  performance_insights_enabled = true

  tags = local.common_tags
}

# ElastiCache Redis
module "elasticache" {
  source = "./modules/elasticache"

  cluster_id = "${local.name_prefix}-redis"

  node_type       = var.redis_node_type
  num_cache_nodes = var.redis_num_nodes

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  security_group_ids = [module.eks.cluster_security_group_id]

  # Replication
  automatic_failover_enabled = var.environment == "production"

  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                = module.kms.key_arn

  tags = local.common_tags
}

# MSK (Kafka)
module "msk" {
  source = "./modules/msk"

  cluster_name = "${local.name_prefix}-kafka"

  kafka_version = var.kafka_version
  broker_count  = var.kafka_broker_count

  instance_type    = var.kafka_instance_type
  ebs_volume_size  = var.kafka_ebs_volume_size

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  security_group_ids = [module.eks.cluster_security_group_id]

  # Encryption
  encryption_in_transit_client_broker = "TLS"
  encryption_at_rest_kms_key_arn      = module.kms.key_arn

  # Monitoring
  enhanced_monitoring = "PER_TOPIC_PER_BROKER"

  tags = local.common_tags
}

# ECR Repositories
module "ecr" {
  source = "./modules/ecr"

  repository_names = [
    "${local.name_prefix}/constitutional-service",
    "${local.name_prefix}/policy-registry",
    "${local.name_prefix}/agent-bus",
    "${local.name_prefix}/api-gateway",
    "${local.name_prefix}/audit-service",
  ]

  image_tag_mutability = "IMMUTABLE"
  scan_on_push        = true

  lifecycle_policy_rules = [
    {
      rulePriority = 1
      description  = "Keep last 30 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = {
        type = "expire"
      }
    }
  ]

  tags = local.common_tags
}

# KMS Key for encryption
module "kms" {
  source  = "terraform-aws-modules/kms/aws"
  version = "~> 2.0"

  description = "ACGS-2 encryption key"
  key_usage   = "ENCRYPT_DECRYPT"

  # Key rotation
  enable_key_rotation = true

  # Policy
  key_administrators = [data.aws_caller_identity.current.arn]
  key_users          = [module.eks.cluster_iam_role_arn]

  aliases = ["${local.name_prefix}-key"]

  tags = local.common_tags
}

# Secrets Manager for database credentials
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${local.name_prefix}/db-credentials"
  description = "ACGS-2 database credentials"
  kms_key_id  = module.kms.key_id

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username             = module.rds.username
    password             = module.rds.password
    host                 = module.rds.endpoint
    port                 = 5432
    database             = module.rds.database_name
    constitutional_hash  = local.constitutional_hash
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "acgs2" {
  name              = "/aws/acgs2/${var.environment}"
  retention_in_days = var.log_retention_days
  kms_key_id        = module.kms.key_arn

  tags = local.common_tags
}

# Route53 Hosted Zone (if domain provided)
resource "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0

  name = var.domain_name

  tags = local.common_tags
}

# ACM Certificate
resource "aws_acm_certificate" "main" {
  count = var.domain_name != "" ? 1 : 0

  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

# Deploy ACGS-2 Helm chart
resource "helm_release" "acgs2" {
  depends_on = [
    module.eks,
    module.rds,
    module.elasticache,
    module.msk,
  ]

  name       = "acgs2"
  chart      = "../../helm/acgs2"
  namespace  = "acgs2"

  create_namespace = true

  values = [
    templatefile("${path.module}/helm-values.yaml.tpl", {
      constitutional_hash     = local.constitutional_hash
      environment            = var.environment
      domain_name            = var.domain_name
      db_host                = module.rds.endpoint
      db_name                = module.rds.database_name
      db_secret_arn          = aws_secretsmanager_secret.db_credentials.arn
      redis_host             = module.elasticache.primary_endpoint_address
      redis_port             = module.elasticache.port
      kafka_bootstrap_servers = module.msk.bootstrap_brokers_tls
      ecr_registry           = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
      image_tag              = var.image_tag
    })
  ]

  set_sensitive {
    name  = "postgresql.auth.password"
    value = module.rds.password
  }

  set_sensitive {
    name  = "redis.auth.password"
    value = module.elasticache.auth_token
  }
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.primary_endpoint_address
}

output "kafka_bootstrap_servers" {
  description = "MSK bootstrap servers"
  value       = module.msk.bootstrap_brokers_tls
}

output "ecr_repository_urls" {
  description = "ECR repository URLs"
  value       = module.ecr.repository_urls
}

output "db_secret_arn" {
  description = "Database credentials secret ARN"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "constitutional_hash" {
  description = "Constitutional hash for validation"
  value       = local.constitutional_hash
}
