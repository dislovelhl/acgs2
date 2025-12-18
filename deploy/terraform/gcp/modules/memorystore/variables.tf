# ACGS-2 Memorystore Module Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "instance_name" {
  description = "Memorystore instance name"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "tier" {
  description = "Service tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "STANDARD_HA"
}

variable "memory_size_gb" {
  description = "Memory size in GB"
  type        = number
  default     = 4
}

variable "authorized_network" {
  description = "VPC network ID"
  type        = string
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "REDIS_7_0"
}

variable "replica_count" {
  description = "Number of read replicas"
  type        = number
  default     = 0
}

variable "read_replicas_mode" {
  description = "Read replicas mode"
  type        = string
  default     = "READ_REPLICAS_DISABLED"
}

variable "transit_encryption_mode" {
  description = "Transit encryption mode"
  type        = string
  default     = "SERVER_AUTHENTICATION"
}

variable "customer_managed_key" {
  description = "Customer managed encryption key"
  type        = string
  default     = null
}

variable "enable_persistence" {
  description = "Enable Redis persistence"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}
