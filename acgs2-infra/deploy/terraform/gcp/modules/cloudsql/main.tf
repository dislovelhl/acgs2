# ACGS-2 Cloud SQL Module
# Constitutional Hash: cdd01ef066bc6cf2

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

locals {
  constitutional_hash = "cdd01ef066bc6cf2"
}

# Random password
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = var.instance_name
  database_version = var.database_version
  region           = var.region

  settings {
    tier              = var.tier
    disk_size         = var.disk_size
    disk_type         = var.disk_type
    disk_autoresize   = var.disk_autoresize
    availability_type = var.availability_type

    # IP configuration
    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_network

      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.value
        }
      }
    }

    # Backup configuration
    backup_configuration {
      enabled                        = var.backup_enabled
      start_time                     = var.backup_start_time
      location                       = var.backup_location
      point_in_time_recovery_enabled = var.point_in_time_recovery
      transaction_log_retention_days = var.transaction_log_retention_days

      backup_retention_settings {
        retained_backups = var.retained_backups
        retention_unit   = "COUNT"
      }
    }

    # Maintenance window
    maintenance_window {
      day          = var.maintenance_window_day
      hour         = var.maintenance_window_hour
      update_track = "stable"
    }

    # Insights config
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    # Database flags
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }

    database_flags {
      name  = "log_statement"
      value = "ddl"
    }

    database_flags {
      name  = "max_connections"
      value = "200"
    }

    database_flags {
      name  = "shared_buffers"
      value = "256000"
    }

    database_flags {
      name  = "work_mem"
      value = "65536"
    }

    user_labels = merge(var.labels, {
      "acgs-io-constitutional-hash" = local.constitutional_hash
    })
  }

  # Encryption
  dynamic "encryption_key_name" {
    for_each = var.encryption_key_name != null ? [1] : []
    content {
      encryption_key_name = var.encryption_key_name
    }
  }

  deletion_protection = var.deletion_protection

  lifecycle {
    prevent_destroy = false
  }
}

# Database
resource "google_sql_database" "main" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
  charset  = "UTF8"
  collation = "en_US.UTF8"
}

# User
resource "google_sql_user" "main" {
  name     = var.user_name
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
  type     = "BUILT_IN"
}

# Read replica (for production)
resource "google_sql_database_instance" "read_replica" {
  count = var.create_read_replica ? 1 : 0

  name                 = "${var.instance_name}-replica"
  database_version     = var.database_version
  region               = var.region
  master_instance_name = google_sql_database_instance.main.name

  replica_configuration {
    failover_target = false
  }

  settings {
    tier            = var.tier
    disk_size       = var.disk_size
    disk_type       = var.disk_type
    disk_autoresize = var.disk_autoresize

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_network
    }

    user_labels = var.labels
  }

  deletion_protection = var.deletion_protection
}

# Outputs
output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.main.name
}

output "connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "private_ip_address" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.main.private_ip_address
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.main.name
}

output "user_name" {
  description = "Database user name"
  value       = google_sql_user.main.name
}

output "user_password" {
  description = "Database user password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "self_link" {
  description = "Cloud SQL instance self link"
  value       = google_sql_database_instance.main.self_link
}
