# ACGS-2 GCP Infrastructure Module
# Constitutional Hash: cdd01ef066bc6cf2

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"

  depends_on = [google_project_service.compute]
}

# Subnets
resource "google_compute_subnetwork" "private" {
  count         = length(var.regions)
  name          = "${var.vpc_name}-private-${var.regions[count.index]}"
  ip_cidr_range = cidrsubnet(var.vpc_cidr, 8, count.index)
  region        = var.regions[count.index]
  network       = google_compute_network.vpc.id

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = cidrsubnet(var.pods_cidr, 8, count.index)
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = cidrsubnet(var.services_cidr, 8, count.index)
  }
}

# GKE Cluster
resource "google_container_cluster" "gke" {
  name                     = var.cluster_name
  location                 = var.regions[0]
  node_locations           = slice(var.regions, 1, length(var.regions))
  network                  = google_compute_network.vpc.id
  subnetwork               = google_compute_subnetwork.private[0].id
  remove_default_node_pool = true
  initial_node_count       = 1

  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Enable GKE Security Posture
  security_posture_config {
    mode = "BASIC"
  }

  # Binary Authorization
  binary_authorization {
    evaluation_mode = var.enable_binary_authorization ? "PROJECT_SINGLETON_POLICY_ENFORCE" : "DISABLED"
  }

  # Network policy
  network_policy {
    enabled = true
  }

  # Addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    gcp_filestore_csi_driver_config {
      enabled = true
    }
  }

  # Maintenance window
  maintenance_policy {
    recurring_window {
      start_time = "2021-01-01T09:00:00Z"
      end_time   = "2021-01-01T17:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA,SU"
    }
  }

  # Monitoring
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
    managed_prometheus {
      enabled = true
    }
  }

  # Logging
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  # Resource usage export to BigQuery
  resource_usage_export_config {
    enable_network_egress_metering = true
    enable_resource_consumption_metering = true
    bigquery_destination {
      dataset_id = google_bigquery_dataset.gke_monitoring.dataset_id
    }
  }

  depends_on = [
    google_project_service.container,
    google_project_service.monitoring,
    google_project_service.logging,
    google_bigquery_dataset.gke_monitoring
  ]
}

# Node Pools
resource "google_container_node_pool" "general" {
  name       = "general"
  cluster    = google_container_cluster.gke.name
  node_count = var.desired_node_count

  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.node_machine_type
    image_type   = "COS_CONTAINERD"

    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    # Shielded instance
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    # Security
    metadata = {
      disable-legacy-endpoints = "true"
    }

    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Labels
    labels = {
      "acgs2/environment" = var.environment
      "acgs2/tenant-id"   = var.tenant_id
    }

    # Taints for general workloads
    dynamic "taint" {
      for_each = var.node_taints
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
}

# High-performance node pool
resource "google_container_node_pool" "high_performance" {
  name       = "high-performance"
  cluster    = google_container_cluster.gke.name
  node_count = 3

  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = "c3-highmem-8"  # High-performance instance
    image_type   = "COS_CONTAINERD"

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      "acgs2/workload-type" = "high-performance"
      "acgs2/service"       = "agent-bus"
    }

    # Taints for high-performance workloads
    taint {
      key    = "workload"
      value  = "high-performance"
      effect = "NO_SCHEDULE"
    }
  }
}

# Cloud SQL PostgreSQL
resource "google_sql_database_instance" "postgresql" {
  name             = "${var.cluster_name}-postgresql"
  database_version = "POSTGRES_15"
  region           = var.regions[0]

  settings {
    tier = var.postgresql_tier

    disk_autoresize = true
    disk_size       = var.postgresql_disk_size
    disk_type       = "PD_SSD"

    backup_configuration {
      enabled    = true
      start_time = "03:00"
      location   = var.regions[0]
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = var.backup_retention_days
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 6  # Saturday
      hour         = 3  # 3 AM
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      record_client_address   = false
      record_application_tags = true
    }

    ip_configuration {
      ipv4_enabled = false
      private_network = google_compute_network.vpc.id
    }

    database_flags {
      name  = "max_connections"
      value = "1000"
    }

    database_flags {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    }
  }

  deletion_protection = var.environment == "production"

  depends_on = [google_project_service.sqladmin]
}

resource "google_sql_database" "acgs2" {
  name     = "acgs2"
  instance = google_sql_database_instance.postgresql.name
}

resource "google_sql_user" "acgs2" {
  name     = "acgs2"
  instance = google_sql_database_instance.postgresql.name
  password = var.postgresql_password
}

# Memorystore Redis
resource "google_redis_instance" "redis" {
  name           = "${var.cluster_name}-redis"
  tier           = "STANDARD_HA"
  memory_size_gb = var.redis_memory_size_gb
  region         = var.regions[0]

  redis_version = "REDIS_7_0"
  display_name  = "ACGS-2 Redis Cache"

  # Security
  auth_enabled = true

  # Persistence
  persistence_config {
    persistence_mode    = "RDB"
    rdb_snapshot_period = "ONE_HOUR"
  }

  # Maintenance
  maintenance_policy {
    weekly_maintenance_window {
      day = "SATURDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }

  depends_on = [google_project_service.redis]
}

# Cloud Pub/Sub for messaging
resource "google_pubsub_topic" "acgs2_events" {
  name = "${var.cluster_name}-events"

  message_retention_duration = "604800s"  # 7 days
  retain_acked_messages      = false

  # Encryption
  kms_key_name = google_kms_crypto_key.pubsub.id

  depends_on = [google_project_service.pubsub]
}

resource "google_pubsub_subscription" "acgs2_events" {
  name  = "${var.cluster_name}-events-sub"
  topic = google_pubsub_topic.acgs2_events.name

  ack_deadline_seconds       = 60
  retain_acked_messages      = false
  enable_message_ordering    = false
  expiration_policy {
    ttl = "300000.5s"  # 3.5 days
  }

  # Dead letter policy
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "dead_letter" {
  name = "${var.cluster_name}-dead-letter"
}

# Cloud Load Balancer
resource "google_compute_global_address" "acgs2" {
  name         = "${var.cluster_name}-address"
  address_type = "EXTERNAL"
}

resource "google_compute_ssl_certificate" "acgs2" {
  name_prefix = "${var.cluster_name}-cert-"
  private_key = var.ssl_private_key
  certificate = var.ssl_certificate

  lifecycle {
    create_before_destroy = true
  }
}

# Cloud Armor (WAF)
resource "google_compute_security_policy" "acgs2" {
  name = "${var.cluster_name}-waf"

  rule {
    action   = "allow"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }

  # Rate limiting
  rule {
    action   = "rate_based_ban"
    priority = "900"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      rate_limit_threshold {
        count        = var.waf_rate_limit
        interval_sec = 300  # 5 minutes
      }
      conform_action = "allow"
      exceed_action  = "deny(403)"
      ban_duration_sec = 3600  # 1 hour
    }
    description = "Rate limiting rule"
  }

  # SQL injection protection
  rule {
    action   = "deny(403)"
    priority = "800"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-canary')"
      }
    }
    description = "SQL injection protection"
  }

  # XSS protection
  rule {
    action   = "deny(403)"
    priority = "700"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-canary')"
      }
    }
    description = "XSS protection"
  }
}

# Cloud DNS
resource "google_dns_managed_zone" "acgs2" {
  count       = var.create_dns_zone ? 1 : 0
  name        = "${var.cluster_name}-zone"
  dns_name    = "${var.dns_domain}."
  description = "ACGS-2 DNS zone"

  depends_on = [google_project_service.dns]
}

resource "google_dns_record_set" "api" {
  count        = var.create_dns_records ? 1 : 0
  name         = "api.${google_dns_managed_zone.acgs2[0].dns_name}"
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.acgs2[0].name
  rrdatas      = [google_compute_global_address.acgs2.address]
}

# Cloud Storage for backups
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-acgs2-backups"
  location      = var.regions[0]
  storage_class = "STANDARD"
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }

  lifecycle_rule {
    condition {
      age = var.backup_retention_days
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.storage]
}

# KMS Keys
resource "google_kms_key_ring" "acgs2" {
  name     = "${var.cluster_name}-keyring"
  location = var.regions[0]

  depends_on = [google_project_service.kms]
}

resource "google_kms_crypto_key" "storage" {
  name     = "storage-key"
  key_ring = google_kms_key_ring.acgs2.id

  purpose = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "pubsub" {
  name     = "pubsub-key"
  key_ring = google_kms_key_ring.acgs2.id

  purpose = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "database" {
  name     = "database-key"
  key_ring = google_kms_key_ring.acgs2.id

  purpose = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# BigQuery for monitoring data
resource "google_bigquery_dataset" "gke_monitoring" {
  dataset_id    = "gke_monitoring"
  friendly_name = "GKE Monitoring Data"
  location      = var.regions[0]

  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }

  access {
    role          = "READER"
    special_group = "projectReaders"
  }

  depends_on = [google_project_service.bigquery]
}

# Service Accounts
resource "google_service_account" "gke_nodes" {
  account_id   = "${var.cluster_name}-gke-nodes"
  display_name = "GKE Nodes Service Account"

  depends_on = [google_project_service.iam]
}

resource "google_project_iam_member" "gke_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "gke_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "gke_monitoring_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

# Enable required APIs
resource "google_project_service" "compute" {
  service = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "container" {
  service = "container.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "sqladmin" {
  service = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "redis" {
  service = "redis.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "pubsub" {
  service = "pubsub.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "kms" {
  service = "cloudkms.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "bigquery" {
  service = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "dns" {
  service = "dns.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "monitoring" {
  service = "monitoring.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "logging" {
  service = "logging.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  service = "iam.googleapis.com"
  disable_on_destroy = false
}

# Outputs
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.gke.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.gke.endpoint
}

output "cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = google_container_cluster.gke.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "subnets" {
  description = "Subnet names"
  value       = google_compute_subnetwork.private[*].name
}

output "load_balancer_ip" {
  description = "Global load balancer IP"
  value       = google_compute_global_address.acgs2.address
}

output "postgresql_instance" {
  description = "PostgreSQL instance name"
  value       = google_sql_database_instance.postgresql.name
}

output "postgresql_connection_name" {
  description = "PostgreSQL connection name"
  value       = google_sql_database_instance.postgresql.connection_name
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.redis.host
}

output "redis_port" {
  description = "Redis port"
  value       = google_redis_instance.redis.port
}

output "pubsub_topic" {
  description = "Pub/Sub topic name"
  value       = google_pubsub_topic.acgs2_events.name
}

output "storage_bucket" {
  description = "Backup storage bucket name"
  value       = google_storage_bucket.backups.name
}

output "kms_keys" {
  description = "KMS key names"
  value = {
    storage = google_kms_crypto_key.storage.name
    pubsub  = google_kms_crypto_key.pubsub.name
    database = google_kms_crypto_key.database.name
  }
}

output "service_account_email" {
  description = "GKE service account email"
  value       = google_service_account.gke_nodes.email
}
