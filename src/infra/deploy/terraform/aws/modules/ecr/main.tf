# ACGS-2 ECR Module
# Constitutional Hash: cdd01ef066bc6cf2

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  constitutional_hash = "cdd01ef066bc6cf2"
}

# ECR Repositories
resource "aws_ecr_repository" "main" {
  for_each = toset(var.repository_names)

  name                 = each.value
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = var.encryption_type
    kms_key         = var.kms_key_arn
  }

  tags = merge(var.tags, {
    "acgs.io/constitutional-hash" = local.constitutional_hash
  })
}

# Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "main" {
  for_each = toset(var.repository_names)

  repository = aws_ecr_repository.main[each.value].name

  policy = jsonencode({
    rules = var.lifecycle_policy_rules
  })
}

# Repository Policy for cross-account access
resource "aws_ecr_repository_policy" "main" {
  for_each = var.enable_cross_account_access ? toset(var.repository_names) : toset([])

  repository = aws_ecr_repository.main[each.value].name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCrossAccountAccess"
        Effect = "Allow"
        Principal = {
          AWS = var.cross_account_principals
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
          "ecr:ListImages"
        ]
      }
    ]
  })
}

# Replication Configuration (for cross-region)
resource "aws_ecr_replication_configuration" "main" {
  count = length(var.replication_regions) > 0 ? 1 : 0

  replication_configuration {
    rule {
      destination {
        region      = var.replication_regions[0]
        registry_id = data.aws_caller_identity.current.account_id
      }

      dynamic "destination" {
        for_each = slice(var.replication_regions, 1, length(var.replication_regions))
        content {
          region      = destination.value
          registry_id = data.aws_caller_identity.current.account_id
        }
      }

      repository_filter {
        filter      = "acgs2"
        filter_type = "PREFIX_MATCH"
      }
    }
  }
}

data "aws_caller_identity" "current" {}

# Outputs
output "repository_urls" {
  description = "ECR repository URLs"
  value = {
    for name, repo in aws_ecr_repository.main : name => repo.repository_url
  }
}

output "repository_arns" {
  description = "ECR repository ARNs"
  value = {
    for name, repo in aws_ecr_repository.main : name => repo.arn
  }
}

output "registry_id" {
  description = "ECR registry ID"
  value       = data.aws_caller_identity.current.account_id
}
