# ACGS-2 MSK Module Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "cluster_name" {
  description = "MSK cluster name"
  type        = string
}

variable "kafka_version" {
  description = "Apache Kafka version"
  type        = string
  default     = "3.5.1"
}

variable "broker_count" {
  description = "Number of broker nodes"
  type        = number
  default     = 3
}

variable "instance_type" {
  description = "Broker instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "ebs_volume_size" {
  description = "EBS volume size in GB"
  type        = number
  default     = 100
}

variable "provisioned_throughput_enabled" {
  description = "Enable provisioned throughput"
  type        = bool
  default     = false
}

variable "volume_throughput" {
  description = "Provisioned throughput in MiB/s"
  type        = number
  default     = 250
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
  description = "Security group IDs allowed to access MSK"
  type        = list(string)
}

variable "encryption_in_transit_client_broker" {
  description = "Encryption in transit (TLS, TLS_PLAINTEXT, PLAINTEXT)"
  type        = string
  default     = "TLS"
}

variable "encryption_at_rest_kms_key_arn" {
  description = "KMS key ARN for at-rest encryption"
  type        = string
  default     = null
}

variable "certificate_authority_arns" {
  description = "ACM Private CA ARNs for client auth"
  type        = list(string)
  default     = []
}

variable "enhanced_monitoring" {
  description = "Enhanced monitoring level"
  type        = string
  default     = "PER_TOPIC_PER_BROKER"

  validation {
    condition     = contains(["DEFAULT", "PER_BROKER", "PER_TOPIC_PER_BROKER", "PER_TOPIC_PER_PARTITION"], var.enhanced_monitoring)
    error_message = "Must be one of: DEFAULT, PER_BROKER, PER_TOPIC_PER_BROKER, PER_TOPIC_PER_PARTITION"
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "create_scram_secret" {
  description = "Create SCRAM secret"
  type        = bool
  default     = false
}

variable "scram_username" {
  description = "SCRAM username"
  type        = string
  default     = "acgs2"
}

variable "scram_password" {
  description = "SCRAM password"
  type        = string
  default     = ""
  sensitive   = true
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
