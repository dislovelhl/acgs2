# ACGS-2 Pub/Sub Module Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "topics" {
  description = "Pub/Sub topics configuration"
  type = map(object({
    message_retention_duration = optional(string, "604800s")
    schema                     = optional(string)
    encoding                   = optional(string, "JSON")
    create_dead_letter         = optional(bool, false)
    subscriptions = map(object({
      ack_deadline_seconds       = optional(number, 60)
      message_retention_duration = optional(string, "604800s")
      retain_acked_messages      = optional(bool, false)
      min_backoff               = optional(string, "10s")
      max_backoff               = optional(string, "600s")
      dead_letter_topic         = optional(string)
      max_delivery_attempts     = optional(number, 5)
      push_endpoint             = optional(string)
      push_service_account      = optional(string)
      expiration_ttl            = optional(string, "")
    }))
  }))
}

variable "kms_key_name" {
  description = "KMS key for encryption"
  type        = string
  default     = null
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}
