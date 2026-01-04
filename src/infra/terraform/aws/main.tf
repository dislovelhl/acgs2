# ACGS-2 AWS Infrastructure Module
# Constitutional Hash: cdd01ef066bc6cf2

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

# VPC Configuration
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = var.vpc_name
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets
  database_subnets = var.database_subnets

  enable_nat_gateway     = true
  single_nat_gateway     = var.environment == "development"
  one_nat_gateway_per_az = var.environment != "development"

  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_max_aggregation_interval    = 60

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
    "acgs2/tenant-id"          = var.tenant_id
    "acgs2/environment"        = var.environment
  })
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    general = {
      name            = "general"
      instance_types  = var.node_instance_types
      min_size        = var.min_node_count
      max_size        = var.max_node_count
      desired_size    = var.desired_node_count
      capacity_type   = "ON_DEMAND"

      # Security group rules
      vpc_security_group_ids = [aws_security_group.eks_nodes.id]

      # IAM roles and policies
      iam_role_additional_policies = {
        AmazonEC2ContainerRegistryReadOnly = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
        AmazonSSMManagedInstanceCore      = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
        CloudWatchAgentServerPolicy       = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
      }

      tags = merge(var.tags, {
        "k8s.io/cluster-autoscaler/enabled" = "true"
        "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
      })
    }

    # High-performance node group for agent bus
    high_performance = {
      name            = "high-performance"
      instance_types  = ["c6i.4xlarge", "c6a.4xlarge"]
      min_size        = 1
      max_size        = 10
      desired_size    = 3
      capacity_type   = "ON_DEMAND"

      vpc_security_group_ids = [aws_security_group.eks_nodes.id]

      iam_role_additional_policies = {
        AmazonEC2ContainerRegistryReadOnly = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
        AmazonSSMManagedInstanceCore      = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
        CloudWatchAgentServerPolicy       = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
      }

      taints = [{
        key    = "workload"
        value  = "high-performance"
        effect = "NO_SCHEDULE"
      }]

      labels = {
        "acgs2/workload-type" = "high-performance"
        "acgs2/service"       = "agent-bus"
      }

      tags = merge(var.tags, {
        "acgs2/workload-type" = "high-performance"
      })
    }
  }

  # Fargate Profile for serverless workloads
  fargate_profiles = {
    default = {
      name = "default"
      selectors = [
        {
          namespace = "kube-system"
          labels = {
            k8s-app = "kube-dns"
          }
        }
      ]
    }
  }

  # CloudWatch Container Insights
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  cloudwatch_log_group_retention_in_days = var.log_retention_days

  # Encryption
  attach_cluster_encryption_policy = true

  # IRSA (IAM Roles for Service Accounts)
  enable_irsa = true

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
    "acgs2/tenant-id"          = var.tenant_id
    "acgs2/environment"        = var.environment
  })
}

# RDS Aurora PostgreSQL
module "aurora_postgresql" {
  source  = "terraform-aws-modules/rds-aurora/aws"
  version = "~> 8.0"

  name           = "${var.cluster_name}-postgresql"
  engine         = "aurora-postgresql"
  engine_version = var.postgresql_version

  vpc_id               = module.vpc.vpc_id
  db_subnet_group_name = aws_db_subnet_group.aurora.name
  security_group_rules = {
    vpc = {
      cidr_blocks = module.vpc.private_subnets_cidr_blocks
    }
  }

  availability_zones = var.availability_zones
  master_username    = var.postgresql_master_username
  database_name      = var.postgresql_database_name

  # Enhanced monitoring
  monitoring_interval = 60
  create_monitoring_role = true
  monitoring_role_name    = "${var.cluster_name}-rds-monitoring"

  # Performance Insights
  performance_insights_enabled = true
  performance_insights_retention_period = 7

  # Backup and recovery
  backup_retention_period = var.backup_retention_days
  preferred_backup_window = "03:00-04:00"
  copy_tags_to_snapshot   = true

  # Maintenance
  preferred_maintenance_window = "sun:04:00-sun:05:00"

  # Scaling
  auto_minor_version_upgrade = true

  instances = {
    1 = {
      instance_class      = var.postgresql_instance_class
      publicly_accessible = false
    }
    2 = {
      instance_class      = var.postgresql_instance_class
      publicly_accessible = false
    }
  }

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
    "acgs2/service"            = "database"
  })
}

# ElastiCache Redis
module "redis" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 1.0"

  cluster_id      = "${var.cluster_name}-redis"
  engine          = "redis"
  engine_version  = var.redis_version
  node_type       = var.redis_node_type
  num_cache_nodes = 1

  # Multi-AZ
  multi_az_enabled = true
  az_mode          = "cross-az"

  # Security
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                = var.redis_auth_token

  # Maintenance
  maintenance_window = "sun:05:00-sun:06:00"

  # Backup
  snapshot_window          = "04:00-05:00"
  snapshot_retention_limit = var.backup_retention_days

  subnet_ids         = module.vpc.database_subnets
  security_group_ids = [aws_security_group.redis.id]

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
    "acgs2/service"            = "cache"
  })
}

# MSK (Managed Streaming for Kafka)
module "msk" {
  source  = "terraform-aws-modules/msk-kafka-cluster/aws"
  version = "~> 2.0"

  name                   = var.cluster_name
  kafka_version         = var.kafka_version
  number_of_broker_nodes = 3

  broker_node_client_subnets  = module.vpc.private_subnets
  broker_node_security_groups = [aws_security_group.msk.id]
  broker_node_storage_info = {
    ebs_storage_volume_size = var.kafka_ebs_volume_size
  }

  broker_node_instance_type = var.kafka_instance_type

  # Encryption
  encryption_in_transit_client_broker = "TLS"
  encryption_in_transit_in_cluster    = true
  encryption_at_rest_kms_key_arn      = aws_kms_key.kafka.arn

  # Monitoring
  cloudwatch_logs_enabled   = true
  cloudwatch_logs_log_group = aws_cloudwatch_log_group.msk.name

  # Configuration
  configuration_name        = "${var.cluster_name}-config"
  configuration_description = "ACGS-2 Kafka configuration"
  configuration_server_properties = {
    "auto.create.topics.enable" = "false"
    "default.replication.factor" = "3"
    "min.insync.replicas"       = "2"
    "num.partitions"           = "12"
    "log.retention.hours"      = "168"
  }

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
    "acgs2/service"            = "messaging"
  })
}

# Application Load Balancer
module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 8.0"

  name = "${var.cluster_name}-alb"

  load_balancer_type = "application"
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnets
  security_groups    = [aws_security_group.alb.id]

  # Access logs
  access_logs = {
    bucket = aws_s3_bucket.alb_logs.id
    prefix = "alb"
  }

  # Listeners
  https_listeners = [
    {
      port               = 443
      protocol           = "HTTPS"
      certificate_arn    = aws_acm_certificate.alb.arn
      target_group_index = 0
    }
  ]

  # Target groups
  target_groups = [
    {
      name             = "${var.cluster_name}-api"
      backend_protocol = "HTTP"
      backend_port     = 80
      target_type      = "ip"
      health_check = {
        enabled             = true
        interval            = 30
        path                = "/health"
        port                = "traffic-port"
        healthy_threshold   = 3
        unhealthy_threshold = 3
        timeout             = 6
        protocol            = "HTTP"
        matcher             = "200-299"
      }
    }
  ]

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
    "acgs2/service"            = "load-balancer"
  })
}

# WAF for ALB
resource "aws_wafv2_web_acl" "alb" {
  name  = "${var.cluster_name}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rate limiting
  rule {
    name     = "RateLimit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "${var.cluster_name}-rate-limit"
      sampled_requests_enabled  = true
    }
  }

  # SQL injection protection
  rule {
    name     = "SQLInjection"
    priority = 2

    action {
      block {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "${var.cluster_name}-sql-injection"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "${var.cluster_name}-waf"
    sampled_requests_enabled  = true
  }

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
  })
}

# CloudFront Distribution (optional)
module "cloudfront" {
  count   = var.enable_cloudfront ? 1 : 0
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "~> 3.0"

  aliases = var.cloudfront_aliases

  comment             = "ACGS-2 CloudFront Distribution"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = var.cloudfront_price_class
  retain_on_delete    = false
  wait_for_deployment = false

  # Origin
  origin = {
    alb = {
      domain_name = module.alb.lb_dns_name
      custom_origin_config = {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  # Default cache behavior
  default_cache_behavior = {
    target_origin_id       = "alb"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods  = ["GET", "HEAD"]
    compress        = true
    query_string    = true
  }

  # WAF
  web_acl_id = aws_wafv2_web_acl.alb.arn

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
  })
}

# Route 53 Records
resource "aws_route53_record" "alb" {
  count = var.create_route53_records ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = module.alb.lb_dns_name
    zone_id               = module.alb.lb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "cloudfront" {
  count = var.enable_cloudfront && var.create_route53_records ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = module.cloudfront[0].cloudfront_distribution_domain_name
    zone_id               = module.cloudfront[0].cloudfront_distribution_hosted_zone_id
    evaluate_target_health = false
  }
}

# ACM Certificate
resource "aws_acm_certificate" "alb" {
  domain_name       = var.api_domain_name
  validation_method = "DNS"

  subject_alternative_names = var.additional_domain_names

  tags = merge(var.tags, {
    "acgs2/constitutional-hash" = "cdd01ef066bc6cf2"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "alb" {
  certificate_arn         = aws_acm_certificate.alb.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# S3 Bucket for ALB logs
resource "aws_s3_bucket" "alb_logs" {
  bucket = "${var.cluster_name}-alb-logs-${random_string.suffix.result}"

  tags = merge(var.tags, {
    "acgs2/service" = "alb-logs"
  })
}

resource "aws_s3_bucket_versioning" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# KMS Keys
resource "aws_kms_key" "kafka" {
  description             = "KMS key for MSK encryption"
  deletion_window_in_days = 7

  tags = merge(var.tags, {
    "acgs2/service" = "kafka"
  })
}

resource "aws_kms_key" "backup" {
  description             = "KMS key for backups"
  deletion_window_in_days = 7

  tags = merge(var.tags, {
    "acgs2/service" = "backup"
  })
}

# Security Groups
resource "aws_security_group" "eks_nodes" {
  name_prefix = "${var.cluster_name}-eks-nodes-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    "acgs2/service" = "eks-nodes"
  })
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.cluster_name}-alb-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    "acgs2/service" = "alb"
  })
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.cluster_name}-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
    description     = "Redis access from EKS"
  }

  tags = merge(var.tags, {
    "acgs2/service" = "redis"
  })
}

resource "aws_security_group" "msk" {
  name_prefix = "${var.cluster_name}-msk-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
    description     = "Kafka access from EKS"
  }

  ingress {
    from_port       = 9094
    to_port         = 9094
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
    description     = "Kafka TLS access from EKS"
  }

  tags = merge(var.tags, {
    "acgs2/service" = "msk"
  })
}

# DB Subnet Group
resource "aws_db_subnet_group" "aurora" {
  name       = "${var.cluster_name}-aurora"
  subnet_ids = module.vpc.database_subnets

  tags = merge(var.tags, {
    "acgs2/service" = "database"
  })
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.cluster_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    "acgs2/service" = "msk"
  })
}

# Random suffix for globally unique resources
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Route 53 validation records for ACM
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.alb.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.route53_zone_id
}

# Outputs
output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.lb_dns_name
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = var.enable_cloudfront ? module.cloudfront[0].cloudfront_distribution_domain_name : null
}

output "postgresql_endpoint" {
  description = "PostgreSQL cluster endpoint"
  value       = module.aurora_postgresql.cluster_endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
}

output "kafka_bootstrap_brokers" {
  description = "MSK bootstrap brokers"
  value       = module.msk.bootstrap_brokers_tls
}
