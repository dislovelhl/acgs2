# ACGS-2 AWS Infrastructure Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production"
  }
}

variable "tenant_id" {
  description = "ACGS-2 tenant ID"
  type        = string
  default     = "acgs2-main"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "acgs2"
}

variable "vpc_name" {
  description = "VPC name"
  type        = string
  default     = "acgs2"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnets" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "database_subnets" {
  description = "Database subnet CIDRs"
  type        = list(string)
  default     = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "node_instance_types" {
  description = "EKS node instance types"
  type        = list(string)
  default     = ["m6i.large", "m6i.xlarge", "m6i.2xlarge"]
}

variable "min_node_count" {
  description = "Minimum number of nodes"
  type        = number
  default     = 3
}

variable "max_node_count" {
  description = "Maximum number of nodes"
  type        = number
  default     = 10
}

variable "desired_node_count" {
  description = "Desired number of nodes"
  type        = number
  default     = 5
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "backup_retention_days" {
  description = "Backup retention in days"
  type        = number
  default     = 30
}

# Database Configuration
variable "postgresql_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15.4"
}

variable "postgresql_instance_class" {
  description = "PostgreSQL instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "postgresql_master_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "acgs2"
}

variable "postgresql_database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "acgs2"
}

# Redis Configuration
variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "7.0"
}

variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_auth_token" {
  description = "Redis auth token"
  type        = string
  sensitive   = true
  default     = null
}

# Kafka Configuration
variable "kafka_version" {
  description = "Kafka version"
  type        = string
  default     = "3.4.0"
}

variable "kafka_instance_type" {
  description = "Kafka instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "kafka_ebs_volume_size" {
  description = "Kafka EBS volume size in GB"
  type        = number
  default     = 100
}

# Domain Configuration
variable "api_domain_name" {
  description = "API domain name"
  type        = string
  default     = "api.acgs2.example.com"
}

variable "additional_domain_names" {
  description = "Additional domain names for certificate"
  type        = list(string)
  default     = []
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID"
  type        = string
  default     = null
}

variable "create_route53_records" {
  description = "Create Route 53 records"
  type        = bool
  default     = false
}

# CloudFront Configuration
variable "enable_cloudfront" {
  description = "Enable CloudFront distribution"
  type        = bool
  default     = false
}

variable "cloudfront_aliases" {
  description = "CloudFront distribution aliases"
  type        = list(string)
  default     = []
}

variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
}

# WAF Configuration
variable "waf_rate_limit" {
  description = "WAF rate limit (requests per 5 minutes)"
  type        = number
  default     = 1000
}

# Tags
variable "tags" {
  description = "Common tags"
  type        = map(string)
  default = {
    "Project"     = "ACGS-2"
    "ManagedBy"   = "Terraform"
    "ConstitutionalHash" = "cdd01ef066bc6cf2"
  }
}

# Enterprise Features
variable "enable_enterprise_features" {
  description = "Enable enterprise features"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Enable enhanced monitoring"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable encryption at rest"
  type        = bool
  default     = true
}

variable "enable_high_availability" {
  description = "Enable high availability configuration"
  type        = bool
  default     = true
}

# Cost Optimization
variable "enable_cost_optimization" {
  description = "Enable cost optimization features"
  type        = bool
  default     = false
}

variable "spot_instance_percentage" {
  description = "Percentage of spot instances (0-100)"
  type        = number
  default     = 0
}

# Compliance
variable "enable_compliance_features" {
  description = "Enable compliance features"
  type        = bool
  default     = true
}

variable "data_residency_region" {
  description = "Data residency region"
  type        = string
  default     = null
}

variable "compliance_frameworks" {
  description = "Compliance frameworks to enable"
  type        = list(string)
  default     = ["SOC2", "GDPR"]
}

# Security
variable "enable_waf" {
  description = "Enable WAF protection"
  type        = bool
  default     = true
}

variable "enable_guardduty" {
  description = "Enable GuardDuty"
  type        = bool
  default     = true
}

variable "enable_config" {
  description = "Enable AWS Config"
  type        = bool
  default     = true
}

variable "enable_cloudtrail" {
  description = "Enable CloudTrail"
  type        = bool
  default     = true
}

# Networking
variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = true
}

variable "vpc_endpoint_services" {
  description = "VPC endpoint services to enable"
  type        = list(string)
  default     = [
    "s3",
    "dynamodb",
    "ec2",
    "ec2messages",
    "ssm",
    "ssmmessages",
    "kms",
    "logs",
    "monitoring"
  ]
}

# Multi-region
variable "enable_multi_region" {
  description = "Enable multi-region deployment"
  type        = bool
  default     = false
}

variable "replica_regions" {
  description = "Replica regions for multi-region deployment"
  type        = list(string)
  default     = []
}

# Disaster Recovery
variable "enable_disaster_recovery" {
  description = "Enable disaster recovery features"
  type        = bool
  default     = false
}

variable "dr_backup_regions" {
  description = "Disaster recovery backup regions"
  type        = list(string)
  default     = []
}

variable "rto_minutes" {
  description = "Recovery Time Objective in minutes"
  type        = number
  default     = 60
}

variable "rpo_minutes" {
  description = "Recovery Point Objective in minutes"
  type        = number
  default     = 15
}
