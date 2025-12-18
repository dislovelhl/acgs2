# ACGS-2 Memorystore Redis Module
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

# Memorystore Redis Instance
resource "google_redis_instance" "main" {
  name           = var.instance_name
  tier           = var.tier
  memory_size_gb = var.memory_size_gb
  region         = var.region

  # Network
  authorized_network = var.authorized_network
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  # Redis configuration
  redis_version = var.redis_version

  redis_configs = {
    maxmemory-policy = "volatile-lru"
    notify-keyspace-events = "Ex"
  }

  # High Availability
  replica_count     = var.replica_count
  read_replicas_mode = var.read_replicas_mode

  # Encryption
  transit_encryption_mode = var.transit_encryption_mode

  dynamic "persistence_config" {
    for_each = var.enable_persistence ? [1] : []
    content {
      persistence_mode    = "RDB"
      rdb_snapshot_period = "ONE_HOUR"
    }
  }

  # Maintenance
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 4
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }

  labels = merge(var.labels, {
    "acgs-io-constitutional-hash" = local.constitutional_hash
  })

  lifecycle {
    prevent_destroy = false
  }
}

# Outputs
output "instance_name" {
  description = "Memorystore instance name"
  value       = google_redis_instance.main.name
}

output "host" {
  description = "Memorystore host"
  value       = google_redis_instance.main.host
}

output "port" {
  description = "Memorystore port"
  value       = google_redis_instance.main.port
}

output "current_location_id" {
  description = "Current location ID"
  value       = google_redis_instance.main.current_location_id
}

output "auth_string" {
  description = "Auth string"
  value       = google_redis_instance.main.auth_string
  sensitive   = true
}

output "server_ca_certs" {
  description = "Server CA certificates"
  value       = google_redis_instance.main.server_ca_certs
  sensitive   = true
}
