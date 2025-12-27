# ACGS-2 ElastiCache Module Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "cluster_id" {
  description = "ElastiCache cluster ID"
  type        = string
}

variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 2
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs allowed to access Redis"
  type        = list(string)
}

variable "automatic_failover_enabled" {
  description = "Enable automatic failover"
  type        = bool
  default     = true
}

variable "at_rest_encryption_enabled" {
  description = "Enable at-rest encryption"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Enable in-transit encryption"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
  default     = null
}

variable "maintenance_window" {
  description = "Maintenance window"
  type        = string
  default     = "sun:05:00-sun:06:00"
}

variable "snapshot_window" {
  description = "Snapshot window"
  type        = string
  default     = "03:00-04:00"
}

variable "snapshot_retention_limit" {
  description = "Snapshot retention limit (days)"
  type        = number
  default     = 7
}

variable "notification_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
  default     = null
}

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alarm_actions" {
  description = "SNS topic ARNs for alarm actions"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
