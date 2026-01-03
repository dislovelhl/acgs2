# ACGS-2 AWS Infrastructure Outputs
# Constitutional Hash: cdd01ef066bc6cf2

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "database_subnets" {
  description = "Database subnet IDs"
  value       = module.vpc.database_subnets
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.alb.lb_dns_name
}

output "alb_zone_id" {
  description = "Application Load Balancer zone ID"
  value       = module.alb.lb_zone_id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = var.enable_cloudfront ? module.cloudfront[0].cloudfront_distribution_domain_name : null
}

output "cloudfront_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID"
  value       = var.enable_cloudfront ? module.cloudfront[0].cloudfront_distribution_hosted_zone_id : null
}

output "postgresql_endpoint" {
  description = "PostgreSQL cluster endpoint"
  value       = module.aurora_postgresql.cluster_endpoint
}

output "postgresql_port" {
  description = "PostgreSQL port"
  value       = module.aurora_postgresql.cluster_port
}

output "postgresql_database_name" {
  description = "PostgreSQL database name"
  value       = module.aurora_postgresql.cluster_database_name
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
}

output "redis_port" {
  description = "Redis port"
  value       = 6379
}

output "kafka_bootstrap_brokers" {
  description = "MSK bootstrap brokers (TLS)"
  value       = module.msk.bootstrap_brokers_tls
}

output "kafka_bootstrap_brokers_plaintext" {
  description = "MSK bootstrap brokers (plaintext)"
  value       = module.msk.bootstrap_brokers
}

output "acm_certificate_arn" {
  description = "ACM certificate ARN"
  value       = aws_acm_certificate.alb.arn
}

output "route53_records" {
  description = "Route 53 records created"
  value = var.create_route53_records ? {
    api = aws_route53_record.alb[0].name
    cloudfront = var.enable_cloudfront ? aws_route53_record.cloudfront[0].name : null
  } : null
}

output "kms_keys" {
  description = "KMS key ARNs"
  value = {
    kafka  = aws_kms_key.kafka.arn
    backup = aws_kms_key.backup.arn
  }
  sensitive = true
}

output "security_groups" {
  description = "Security group IDs"
  value = {
    eks_nodes = aws_security_group.eks_nodes.id
    alb       = aws_security_group.alb.id
    redis     = aws_security_group.redis.id
    msk       = aws_security_group.msk.id
  }
}

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    alb_logs = aws_s3_bucket.alb_logs.bucket
  }
}

output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN"
  value       = aws_wafv2_web_acl.alb.arn
}

# Enterprise-specific outputs
output "enterprise_features" {
  description = "Enterprise features status"
  value = {
    high_availability = var.enable_high_availability
    backup_enabled    = var.enable_backup
    encryption_enabled = var.enable_encryption
    monitoring_enabled = var.enable_monitoring
    compliance_enabled = var.enable_compliance_features
    multi_region_enabled = var.enable_multi_region
    disaster_recovery_enabled = var.enable_disaster_recovery
  }
}

output "compliance_configuration" {
  description = "Compliance configuration"
  value = {
    frameworks = var.compliance_frameworks
    data_residency = var.data_residency_region
    encryption_at_rest = var.enable_encryption
    audit_logging = var.enable_cloudtrail
  }
}

output "cost_optimization" {
  description = "Cost optimization settings"
  value = {
    enabled = var.enable_cost_optimization
    spot_instance_percentage = var.spot_instance_percentage
  }
}

output "monitoring_endpoints" {
  description = "Monitoring and observability endpoints"
  value = {
    cloudwatch_logs = "/aws/eks/${var.cluster_name}/containers"
    prometheus = "prometheus.${var.api_domain_name}"
    grafana = "grafana.${var.api_domain_name}"
    kibana = "kibana.${var.api_domain_name}"
  }
}

output "backup_configuration" {
  description = "Backup configuration"
  value = {
    aurora_backup_retention = var.backup_retention_days
    redis_snapshot_retention = var.backup_retention_days
    kms_key_arn = aws_kms_key.backup.arn
  }
}

output "networking_configuration" {
  description = "Networking configuration"
  value = {
    vpc_id = module.vpc.vpc_id
    vpc_endpoints_enabled = var.enable_vpc_endpoints
    waf_enabled = var.enable_waf
    cloudfront_enabled = var.enable_cloudfront
  }
}

# Kubernetes configuration for Helm
output "kubernetes_config" {
  description = "Kubernetes configuration for Helm deployments"
  value = {
    cluster_name = module.eks.cluster_name
    cluster_endpoint = module.eks.cluster_endpoint
    cluster_ca_cert = module.eks.cluster_certificate_authority_data
    oidc_provider_arn = module.eks.oidc_provider_arn
    oidc_provider_url = module.eks.cluster_oidc_issuer_url
  }
  sensitive = true
}

# Helm values for ACGS-2 deployment
output "helm_values" {
  description = "Helm values for ACGS-2 deployment"
  value = {
    global = {
      env = var.environment
      tenantId = var.tenant_id
      constitutionalHash = "cdd01ef066bc6cf2"
    }
    externalDatabase = {
      url = "postgresql://${var.postgresql_master_username}:PASSWORD@${module.aurora_postgresql.cluster_endpoint}:${module.aurora_postgresql.cluster_port}/${var.postgresql_database_name}"
    }
    externalRedis = {
      url = "redis://${module.redis.endpoint}:${var.redis_port}"
    }
    externalKafka = {
      bootstrapServers = module.msk.bootstrap_brokers_tls[0]
    }
    ingress = {
      enabled = true
      hosts = [{
        host = var.api_domain_name
        paths = [{
          path = "/"
          pathType = "Prefix"
        }]
      }]
    }
  }
  sensitive = true
}
