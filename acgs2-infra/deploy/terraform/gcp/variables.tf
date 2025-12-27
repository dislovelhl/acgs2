# ACGS-2 GCP Terraform Variables
# Constitutional Hash: cdd01ef066bc6cf2

# ============================================================================
# General
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production"
  }
}

variable "cost_center" {
  description = "Cost center for resource labeling"
  type        = string
  default     = "acgs2"
}

variable "owner" {
  description = "Owner for resource labeling"
  type        = string
  default     = "acgs-team"
}

# ============================================================================
# Networking
# ============================================================================

variable "gke_subnet_cidr" {
  description = "GKE subnet CIDR"
  type        = string
  default     = "10.0.0.0/20"
}

variable "db_subnet_cidr" {
  description = "Database subnet CIDR"
  type        = string
  default     = "10.0.16.0/24"
}

variable "pods_cidr" {
  description = "GKE pods secondary range CIDR"
  type        = string
  default     = "10.4.0.0/14"
}

variable "services_cidr" {
  description = "GKE services secondary range CIDR"
  type        = string
  default     = "10.8.0.0/20"
}

variable "master_cidr" {
  description = "GKE master CIDR for private cluster"
  type        = string
  default     = "172.16.0.0/28"
}

# ============================================================================
# GKE
# ============================================================================

variable "gke_version" {
  description = "GKE version"
  type        = string
  default     = "1.28"
}

variable "gke_machine_type" {
  description = "GKE node machine type (for Standard mode)"
  type        = string
  default     = "e2-standard-4"
}

variable "gke_min_nodes" {
  description = "Minimum number of GKE nodes"
  type        = number
  default     = 1
}

variable "gke_max_nodes" {
  description = "Maximum number of GKE nodes"
  type        = number
  default     = 10
}

# ============================================================================
# Cloud SQL
# ============================================================================

variable "db_version" {
  description = "Cloud SQL PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "db_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-custom-2-7680"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 100
}

# ============================================================================
# Memorystore Redis
# ============================================================================

variable "redis_tier" {
  description = "Memorystore Redis tier"
  type        = string
  default     = "STANDARD_HA"
}

variable "redis_memory_gb" {
  description = "Memorystore Redis memory in GB"
  type        = number
  default     = 4
}

# ============================================================================
# Application
# ============================================================================

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}
