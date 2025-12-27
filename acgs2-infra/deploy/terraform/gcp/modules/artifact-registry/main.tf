# ACGS-2 Artifact Registry Module
# Constitutional Hash: cdd01ef066bc6cf2

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

locals {
  constitutional_hash = "cdd01ef066bc6cf2"
}

# Artifact Registry Repositories
resource "google_artifact_registry_repository" "main" {
  for_each = var.repositories

  location      = var.location
  repository_id = each.key
  description   = each.value.description
  format        = each.value.format

  # Encryption
  kms_key_name = var.kms_key_name

  # Cleanup policies
  dynamic "cleanup_policies" {
    for_each = lookup(each.value, "cleanup_policies", [])
    content {
      id     = cleanup_policies.value.id
      action = cleanup_policies.value.action

      dynamic "condition" {
        for_each = lookup(cleanup_policies.value, "condition", null) != null ? [1] : []
        content {
          tag_state    = lookup(cleanup_policies.value.condition, "tag_state", null)
          tag_prefixes = lookup(cleanup_policies.value.condition, "tag_prefixes", null)
          older_than   = lookup(cleanup_policies.value.condition, "older_than", null)
        }
      }

      dynamic "most_recent_versions" {
        for_each = lookup(cleanup_policies.value, "most_recent_versions", null) != null ? [1] : []
        content {
          keep_count = cleanup_policies.value.most_recent_versions.keep_count
        }
      }
    }
  }

  labels = merge(var.labels, {
    "acgs-io-constitutional-hash" = local.constitutional_hash
  })
}

# Default cleanup policy for all repositories
resource "google_artifact_registry_repository" "cleanup" {
  for_each = { for k, v in var.repositories : k => v if lookup(v, "enable_default_cleanup", true) }

  location      = var.location
  repository_id = each.key
  description   = each.value.description
  format        = each.value.format

  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"

    most_recent_versions {
      keep_count = var.default_keep_count
    }
  }

  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"

    condition {
      tag_state  = "UNTAGGED"
      older_than = var.default_untagged_retention
    }
  }

  kms_key_name = var.kms_key_name

  labels = var.labels

  lifecycle {
    ignore_changes = [cleanup_policies]
  }
}

# IAM Bindings for repositories
resource "google_artifact_registry_repository_iam_member" "readers" {
  for_each = merge([
    for repo_name, repo_config in var.repositories : {
      for reader in lookup(repo_config, "readers", []) :
      "${repo_name}-${reader}" => {
        repository = repo_name
        member     = reader
      }
    }
  ]...)

  project    = var.project_id
  location   = var.location
  repository = google_artifact_registry_repository.main[each.value.repository].name
  role       = "roles/artifactregistry.reader"
  member     = each.value.member
}

resource "google_artifact_registry_repository_iam_member" "writers" {
  for_each = merge([
    for repo_name, repo_config in var.repositories : {
      for writer in lookup(repo_config, "writers", []) :
      "${repo_name}-${writer}" => {
        repository = repo_name
        member     = writer
      }
    }
  ]...)

  project    = var.project_id
  location   = var.location
  repository = google_artifact_registry_repository.main[each.value.repository].name
  role       = "roles/artifactregistry.writer"
  member     = each.value.member
}

# Outputs
output "repository_ids" {
  description = "Artifact Registry repository IDs"
  value       = { for k, v in google_artifact_registry_repository.main : k => v.id }
}

output "repository_names" {
  description = "Artifact Registry repository names"
  value       = { for k, v in google_artifact_registry_repository.main : k => v.name }
}

output "docker_urls" {
  description = "Docker repository URLs"
  value = {
    for k, v in google_artifact_registry_repository.main :
    k => "${var.location}-docker.pkg.dev/${var.project_id}/${v.name}"
    if v.format == "DOCKER"
  }
}
