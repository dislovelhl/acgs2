# ACGS-2 Pub/Sub Module
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

# Pub/Sub Topics
resource "google_pubsub_topic" "main" {
  for_each = var.topics

  name = each.key

  message_retention_duration = each.value.message_retention_duration

  dynamic "schema_settings" {
    for_each = each.value.schema != null ? [1] : []
    content {
      schema   = each.value.schema
      encoding = each.value.encoding
    }
  }

  # Encryption
  kms_key_name = var.kms_key_name

  labels = merge(var.labels, {
    "acgs-io-constitutional-hash" = local.constitutional_hash
  })
}

# Pub/Sub Subscriptions
resource "google_pubsub_subscription" "main" {
  for_each = merge([
    for topic_name, topic_config in var.topics : {
      for sub_name, sub_config in topic_config.subscriptions :
      "${topic_name}-${sub_name}" => merge(sub_config, {
        topic_name = topic_name
        sub_name   = sub_name
      })
    }
  ]...)

  name  = each.value.sub_name
  topic = google_pubsub_topic.main[each.value.topic_name].name

  ack_deadline_seconds = each.value.ack_deadline_seconds

  message_retention_duration = lookup(each.value, "message_retention_duration", "604800s")
  retain_acked_messages     = lookup(each.value, "retain_acked_messages", false)

  # Retry policy
  retry_policy {
    minimum_backoff = lookup(each.value, "min_backoff", "10s")
    maximum_backoff = lookup(each.value, "max_backoff", "600s")
  }

  # Dead letter policy
  dynamic "dead_letter_policy" {
    for_each = lookup(each.value, "dead_letter_topic", null) != null ? [1] : []
    content {
      dead_letter_topic     = each.value.dead_letter_topic
      max_delivery_attempts = lookup(each.value, "max_delivery_attempts", 5)
    }
  }

  # Push config (if specified)
  dynamic "push_config" {
    for_each = lookup(each.value, "push_endpoint", null) != null ? [1] : []
    content {
      push_endpoint = each.value.push_endpoint

      dynamic "oidc_token" {
        for_each = lookup(each.value, "push_service_account", null) != null ? [1] : []
        content {
          service_account_email = each.value.push_service_account
        }
      }
    }
  }

  # Expiration policy
  expiration_policy {
    ttl = lookup(each.value, "expiration_ttl", "")
  }

  labels = var.labels
}

# Dead Letter Topics (automatically created for topics that need them)
resource "google_pubsub_topic" "dead_letter" {
  for_each = toset([
    for topic_name, topic_config in var.topics :
    topic_name if lookup(topic_config, "create_dead_letter", false)
  ])

  name = "${each.value}-dlq"

  message_retention_duration = "2592000s" # 30 days

  kms_key_name = var.kms_key_name

  labels = merge(var.labels, {
    "acgs-io-constitutional-hash" = local.constitutional_hash
    "dead-letter-for"              = each.value
  })
}

# Outputs
output "topic_names" {
  description = "Pub/Sub topic names"
  value       = { for k, v in google_pubsub_topic.main : k => v.name }
}

output "topic_ids" {
  description = "Pub/Sub topic IDs"
  value       = { for k, v in google_pubsub_topic.main : k => v.id }
}

output "subscription_names" {
  description = "Pub/Sub subscription names"
  value       = { for k, v in google_pubsub_subscription.main : k => v.name }
}

output "subscription_ids" {
  description = "Pub/Sub subscription IDs"
  value       = { for k, v in google_pubsub_subscription.main : k => v.id }
}
