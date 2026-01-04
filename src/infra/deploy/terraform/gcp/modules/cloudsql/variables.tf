# ACGS-2 Cloud SQL Module Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "instance_name" {
  description = "Cloud SQL instance name"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "tier" {
  description = "Machine tier"
  type        = string
  default     = "db-custom-2-7680"
}

variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 100
}

variable "disk_type" {
  description = "Disk type"
  type        = string
  default     = "PD_SSD"
}

variable "disk_autoresize" {
  description = "Enable disk autoresize"
  type        = bool
  default     = true
}

variable "availability_type" {
  description = "Availability type (ZONAL or REGIONAL)"
  type        = string
  default     = "ZONAL"
}

variable "vpc_network" {
  description = "VPC network ID"
  type        = string
}

variable "authorized_networks" {
  description = "Authorized networks"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "user_name" {
  description = "Database user name"
  type        = string
}

variable "backup_enabled" {
  description = "Enable backups"
  type        = bool
  default     = true
}

variable "backup_start_time" {
  description = "Backup start time"
  type        = string
  default     = "03:00"
}

variable "backup_location" {
  description = "Backup location"
  type        = string
  default     = null
}

variable "point_in_time_recovery" {
  description = "Enable point-in-time recovery"
  type        = bool
  default     = true
}

variable "transaction_log_retention_days" {
  description = "Transaction log retention days"
  type        = number
  default     = 7
}

variable "retained_backups" {
  description = "Number of retained backups"
  type        = number
  default     = 7
}

variable "maintenance_window_day" {
  description = "Maintenance window day (1-7)"
  type        = number
  default     = 1
}

variable "maintenance_window_hour" {
  description = "Maintenance window hour (0-23)"
  type        = number
  default     = 4
}

variable "encryption_key_name" {
  description = "KMS key for encryption"
  type        = string
  default     = null
}

variable "create_read_replica" {
  description = "Create read replica"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}
