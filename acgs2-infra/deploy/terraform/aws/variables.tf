# ACGS-2 AWS Terraform Variables
# Constitutional Hash: cdd01ef066bc6cf2

# ============================================================================
# General
# ============================================================================

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production"
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "cost_center" {
  description = "Cost center for resource tagging"
  type        = string
  default     = "acgs2"
}

variable "owner" {
  description = "Owner for resource tagging"
  type        = string
  default     = "acgs-team"
}

# ============================================================================
# Networking
# ============================================================================

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# ============================================================================
# EKS
# ============================================================================

variable "eks_cluster_version" {
  description = "EKS cluster Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "eks_node_groups" {
  description = "EKS node group configurations"
  type = map(object({
    instance_types = list(string)
    capacity_type  = string
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
    labels         = map(string)
    taints = list(object({
      key    = string
      value  = string
      effect = string
    }))
  }))
  default = {
    general = {
      instance_types = ["m6i.large", "m5.large"]
      capacity_type  = "ON_DEMAND"
      min_size       = 2
      max_size       = 10
      desired_size   = 3
      disk_size      = 50
      labels = {
        role = "general"
      }
      taints = []
    }
    constitutional = {
      instance_types = ["m6i.xlarge", "m5.xlarge"]
      capacity_type  = "ON_DEMAND"
      min_size       = 2
      max_size       = 8
      desired_size   = 2
      disk_size      = 100
      labels = {
        role = "constitutional"
      }
      taints = [
        {
          key    = "workload"
          value  = "constitutional"
          effect = "NO_SCHEDULE"
        }
      ]
    }
  }
}

# ============================================================================
# RDS PostgreSQL
# ============================================================================

variable "rds_engine_version" {
  description = "RDS PostgreSQL engine version"
  type        = string
  default     = "15.4"
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "rds_backup_retention" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

# ============================================================================
# ElastiCache Redis
# ============================================================================

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_num_nodes" {
  description = "Number of Redis cache nodes"
  type        = number
  default     = 2
}

# ============================================================================
# MSK (Kafka)
# ============================================================================

variable "kafka_version" {
  description = "Apache Kafka version"
  type        = string
  default     = "3.5.1"
}

variable "kafka_broker_count" {
  description = "Number of Kafka broker nodes"
  type        = number
  default     = 3
}

variable "kafka_instance_type" {
  description = "Kafka broker instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "kafka_ebs_volume_size" {
  description = "Kafka EBS volume size in GB"
  type        = number
  default     = 100
}

# ============================================================================
# Logging
# ============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# ============================================================================
# Domain
# ============================================================================

variable "domain_name" {
  description = "Domain name for ACGS-2 (optional)"
  type        = string
  default     = ""
}

# ============================================================================
# Application
# ============================================================================

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}
