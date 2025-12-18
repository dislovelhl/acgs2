# ACGS-2 ElastiCache Redis Module
# Constitutional Hash: cdd01ef066bc6cf2

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

locals {
  constitutional_hash = "cdd01ef066bc6cf2"
}

# Auth token for Redis
resource "random_password" "auth_token" {
  length           = 32
  special          = false
}

# Security Group
resource "aws_security_group" "redis" {
  name        = "${var.cluster_id}-sg"
  description = "Security group for ACGS-2 Redis"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from EKS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.security_group_ids
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_id}-sg"
  })
}

# Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name        = "${var.cluster_id}-subnet-group"
  description = "Subnet group for ACGS-2 Redis"
  subnet_ids  = var.subnet_ids

  tags = var.tags
}

# Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name        = "${var.cluster_id}-pg"
  family      = "redis7"
  description = "Parameter group for ACGS-2 Redis"

  # Performance tuning
  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru"
  }

  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"
  }

  # TCP keepalive
  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }

  tags = var.tags
}

# Replication Group (Redis Cluster)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = var.cluster_id
  description          = "ACGS-2 Redis cluster"

  # Engine
  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_nodes
  port                 = 6379

  # Network
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  # Parameter Group
  parameter_group_name = aws_elasticache_parameter_group.main.name

  # High Availability
  automatic_failover_enabled = var.automatic_failover_enabled
  multi_az_enabled          = var.automatic_failover_enabled

  # Encryption
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  kms_key_id                = var.kms_key_id
  auth_token                = var.transit_encryption_enabled ? random_password.auth_token.result : null

  # Maintenance
  maintenance_window       = var.maintenance_window
  snapshot_window         = var.snapshot_window
  snapshot_retention_limit = var.snapshot_retention_limit

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Notifications
  notification_topic_arn = var.notification_topic_arn

  tags = merge(var.tags, {
    "acgs.io/constitutional-hash" = local.constitutional_hash
  })

  lifecycle {
    ignore_changes = [auth_token]
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.cluster_id}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis CPU utilization is high"

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.alarm_actions

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "memory" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.cluster_id}-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis memory usage is high"

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.alarm_actions

  tags = var.tags
}

# Outputs
output "primary_endpoint_address" {
  description = "Primary endpoint address"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "reader_endpoint_address" {
  description = "Reader endpoint address"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
}

output "port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "auth_token" {
  description = "Redis auth token"
  value       = random_password.auth_token.result
  sensitive   = true
}

output "arn" {
  description = "Replication group ARN"
  value       = aws_elasticache_replication_group.main.arn
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.redis.id
}
