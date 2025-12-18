# ACGS-2 GCP Infrastructure
# Constitutional Hash: cdd01ef066bc6cf2
#
# This Terraform configuration deploys ACGS-2 on GCP with:
# - GKE Autopilot cluster for Kubernetes workloads
# - Cloud SQL PostgreSQL for persistent storage
# - Memorystore Redis for caching
# - Pub/Sub for event streaming
# - Artifact Registry for container images

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  backend "gcs" {
    # Configure in terraform.tfvars or via CLI
    # bucket = "acgs2-terraform-state"
    # prefix = "gcp/terraform/state"
  }
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Local values
locals {
  constitutional_hash = "cdd01ef066bc6cf2"

  labels = {
    project             = "acgs2"
    environment         = var.environment
    managed-by          = "terraform"
    constitutional-hash = local.constitutional_hash
    cost-center         = var.cost_center
    owner               = var.owner
  }

  name_prefix = "acgs2-${var.environment}"
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "pubsub.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudkms.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "servicenetworking.googleapis.com",
    "iap.googleapis.com",
    "certificatemanager.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# VPC Network
module "vpc" {
  source  = "terraform-google-modules/network/google"
  version = "~> 9.0"

  project_id   = var.project_id
  network_name = "${local.name_prefix}-vpc"

  subnets = [
    {
      subnet_name           = "${local.name_prefix}-gke"
      subnet_ip             = var.gke_subnet_cidr
      subnet_region         = var.region
      subnet_private_access = true
      subnet_flow_logs      = true
    },
    {
      subnet_name           = "${local.name_prefix}-db"
      subnet_ip             = var.db_subnet_cidr
      subnet_region         = var.region
      subnet_private_access = true
    }
  ]

  secondary_ranges = {
    "${local.name_prefix}-gke" = [
      {
        range_name    = "pods"
        ip_cidr_range = var.pods_cidr
      },
      {
        range_name    = "services"
        ip_cidr_range = var.services_cidr
      }
    ]
  }

  routes = [
    {
      name              = "egress-internet"
      description       = "Route through IGW to access internet"
      destination_range = "0.0.0.0/0"
      tags              = "egress-inet"
      next_hop_internet = true
    }
  ]

  depends_on = [google_project_service.services]
}

# Cloud NAT for private GKE
module "cloud_nat" {
  source  = "terraform-google-modules/cloud-nat/google"
  version = "~> 5.0"

  project_id    = var.project_id
  region        = var.region
  router        = "${local.name_prefix}-router"
  network       = module.vpc.network_name
  create_router = true
}

# Private Service Access for Cloud SQL
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "${local.name_prefix}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = module.vpc.network_id

  depends_on = [google_project_service.services]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = module.vpc.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]

  depends_on = [google_project_service.services]
}

# KMS Key Ring and Key
resource "google_kms_key_ring" "main" {
  name     = "${local.name_prefix}-keyring"
  location = var.region

  depends_on = [google_project_service.services]
}

resource "google_kms_crypto_key" "main" {
  name            = "${local.name_prefix}-key"
  key_ring        = google_kms_key_ring.main.id
  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  labels = local.labels
}

# GKE Autopilot Cluster
module "gke" {
  source = "./modules/gke"

  project_id   = var.project_id
  cluster_name = local.name_prefix
  region       = var.region

  network           = module.vpc.network_name
  subnetwork        = "${local.name_prefix}-gke"
  pods_range_name   = "pods"
  svc_range_name    = "services"

  # Workload Identity
  enable_workload_identity = true

  # Security
  enable_private_nodes    = true
  master_ipv4_cidr_block = var.master_cidr
  enable_binary_authorization = var.environment == "production"

  # Encryption
  database_encryption_key = google_kms_crypto_key.main.id

  labels = local.labels

  depends_on = [
    module.vpc,
    google_project_service.services,
  ]
}

# Cloud SQL PostgreSQL
module "cloudsql" {
  source = "./modules/cloudsql"

  project_id    = var.project_id
  instance_name = "${local.name_prefix}-db"
  region        = var.region

  database_version = var.db_version
  tier            = var.db_tier
  disk_size       = var.db_disk_size

  database_name = "acgs"
  user_name     = "acgs_admin"

  # Network
  vpc_network = module.vpc.network_id

  # High Availability
  availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"

  # Encryption
  encryption_key_name = google_kms_crypto_key.main.id

  # Backup
  backup_enabled = true
  backup_start_time = "03:00"
  backup_location   = var.region

  # Maintenance
  maintenance_window_day  = 1
  maintenance_window_hour = 4

  labels = local.labels

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.services,
  ]
}

# Memorystore Redis
module "memorystore" {
  source = "./modules/memorystore"

  project_id    = var.project_id
  instance_name = "${local.name_prefix}-redis"
  region        = var.region

  tier          = var.redis_tier
  memory_size_gb = var.redis_memory_gb

  # Network
  authorized_network = module.vpc.network_id

  # High Availability
  replica_count = var.environment == "production" ? 1 : 0
  read_replicas_mode = var.environment == "production" ? "READ_REPLICAS_ENABLED" : "READ_REPLICAS_DISABLED"

  # Encryption
  transit_encryption_mode = "SERVER_AUTHENTICATION"
  customer_managed_key    = google_kms_crypto_key.main.id

  labels = local.labels

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.services,
  ]
}

# Pub/Sub Topics
module "pubsub" {
  source = "./modules/pubsub"

  project_id = var.project_id

  topics = {
    "acgs-agent-messages" = {
      message_retention_duration = "604800s" # 7 days
      subscriptions = {
        "agent-bus" = {
          ack_deadline_seconds = 60
          retain_acked_messages = false
          message_retention_duration = "604800s"
        }
      }
    }
    "acgs-agent-events" = {
      message_retention_duration = "604800s"
      subscriptions = {
        "event-processor" = {
          ack_deadline_seconds = 60
        }
      }
    }
    "acgs-governance-dlq" = {
      message_retention_duration = "2592000s" # 30 days
      subscriptions = {
        "dlq-processor" = {
          ack_deadline_seconds = 120
        }
      }
    }
  }

  # Encryption
  kms_key_name = google_kms_crypto_key.main.id

  labels = local.labels

  depends_on = [google_project_service.services]
}

# Artifact Registry
module "artifact_registry" {
  source = "./modules/artifact-registry"

  project_id = var.project_id
  location   = var.region

  repositories = {
    "acgs2-images" = {
      description = "ACGS-2 container images"
      format      = "DOCKER"
    }
    "acgs2-helm" = {
      description = "ACGS-2 Helm charts"
      format      = "DOCKER"
    }
  }

  # Encryption
  kms_key_name = google_kms_crypto_key.main.id

  labels = local.labels

  depends_on = [google_project_service.services]
}

# Secret Manager for database credentials
resource "google_secret_manager_secret" "db_credentials" {
  secret_id = "${local.name_prefix}-db-credentials"

  replication {
    auto {
      customer_managed_encryption {
        kms_key_name = google_kms_crypto_key.main.id
      }
    }
  }

  labels = local.labels

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "db_credentials" {
  secret = google_secret_manager_secret.db_credentials.id
  secret_data = jsonencode({
    username            = module.cloudsql.user_name
    password            = module.cloudsql.user_password
    host                = module.cloudsql.private_ip_address
    port                = 5432
    database            = module.cloudsql.database_name
    connection_name     = module.cloudsql.connection_name
    constitutional_hash = local.constitutional_hash
  })
}

# Workload Identity for ACGS-2
resource "google_service_account" "acgs2" {
  account_id   = "${local.name_prefix}-sa"
  display_name = "ACGS-2 Workload Identity"
  description  = "Service account for ACGS-2 workloads"
}

resource "google_project_iam_member" "acgs2_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/cloudkms.cryptoKeyEncrypterDecrypter",
    "roles/cloudsql.client",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.acgs2.email}"
}

resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.acgs2.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[acgs2/acgs2]"

  depends_on = [module.gke]
}

# Deploy ACGS-2 Helm chart
resource "helm_release" "acgs2" {
  depends_on = [
    module.gke,
    module.cloudsql,
    module.memorystore,
    module.pubsub,
  ]

  name       = "acgs2"
  chart      = "../../helm/acgs2"
  namespace  = "acgs2"

  create_namespace = true

  values = [
    templatefile("${path.module}/helm-values.yaml.tpl", {
      constitutional_hash    = local.constitutional_hash
      environment           = var.environment
      project_id            = var.project_id
      region                = var.region
      db_connection_name    = module.cloudsql.connection_name
      db_secret_name        = google_secret_manager_secret.db_credentials.secret_id
      redis_host            = module.memorystore.host
      redis_port            = module.memorystore.port
      service_account_email = google_service_account.acgs2.email
      artifact_registry     = "${var.region}-docker.pkg.dev/${var.project_id}/acgs2-images"
      image_tag             = var.image_tag
    })
  ]
}

# Outputs
output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "vpc_network" {
  description = "VPC network name"
  value       = module.vpc.network_name
}

output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = module.gke.cluster_name
}

output "gke_cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = module.gke.cluster_endpoint
  sensitive   = true
}

output "cloudsql_connection_name" {
  description = "Cloud SQL connection name"
  value       = module.cloudsql.connection_name
}

output "cloudsql_private_ip" {
  description = "Cloud SQL private IP"
  value       = module.cloudsql.private_ip_address
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = module.memorystore.host
}

output "pubsub_topics" {
  description = "Pub/Sub topic names"
  value       = module.pubsub.topic_names
}

output "artifact_registry_url" {
  description = "Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/acgs2-images"
}

output "service_account_email" {
  description = "ACGS-2 service account email"
  value       = google_service_account.acgs2.email
}

output "db_secret_name" {
  description = "Database credentials secret name"
  value       = google_secret_manager_secret.db_credentials.secret_id
}

output "constitutional_hash" {
  description = "Constitutional hash for validation"
  value       = local.constitutional_hash
}
