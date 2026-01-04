# ACGS-2 ECR Module Variables
# Constitutional Hash: cdd01ef066bc6cf2

variable "repository_names" {
  description = "List of ECR repository names"
  type        = list(string)
}

variable "image_tag_mutability" {
  description = "Image tag mutability (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "IMMUTABLE"
}

variable "scan_on_push" {
  description = "Enable vulnerability scanning on push"
  type        = bool
  default     = true
}

variable "encryption_type" {
  description = "Encryption type (AES256 or KMS)"
  type        = string
  default     = "KMS"
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
  default     = null
}

variable "lifecycle_policy_rules" {
  description = "ECR lifecycle policy rules"
  type        = any
  default = [
    {
      rulePriority = 1
      description  = "Keep last 30 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = {
        type = "expire"
      }
    }
  ]
}

variable "enable_cross_account_access" {
  description = "Enable cross-account access"
  type        = bool
  default     = false
}

variable "cross_account_principals" {
  description = "Cross-account principals for repository access"
  type        = list(string)
  default     = []
}

variable "replication_regions" {
  description = "Regions for ECR replication"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
