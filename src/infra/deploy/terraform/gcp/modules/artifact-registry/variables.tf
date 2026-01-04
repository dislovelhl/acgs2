# ACGS-2 Artifact Registry Module Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "location" {
  description = "Artifact Registry location"
  type        = string
}

variable "repositories" {
  description = "Artifact Registry repositories"
  type = map(object({
    description            = string
    format                 = string
    enable_default_cleanup = optional(bool, true)
    readers                = optional(list(string), [])
    writers                = optional(list(string), [])
    cleanup_policies = optional(list(object({
      id     = string
      action = string
      condition = optional(object({
        tag_state    = optional(string)
        tag_prefixes = optional(list(string))
        older_than   = optional(string)
      }))
      most_recent_versions = optional(object({
        keep_count = number
      }))
    })), [])
  }))
}

variable "kms_key_name" {
  description = "KMS key for encryption"
  type        = string
  default     = null
}

variable "default_keep_count" {
  description = "Default number of versions to keep"
  type        = number
  default     = 30
}

variable "default_untagged_retention" {
  description = "Default retention for untagged images"
  type        = string
  default     = "604800s" # 7 days
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}
