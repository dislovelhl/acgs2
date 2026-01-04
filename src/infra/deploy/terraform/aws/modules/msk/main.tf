# ACGS-2 MSK (Kafka) Module
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

# Security Group
resource "aws_security_group" "msk" {
  name        = "${var.cluster_name}-sg"
  description = "Security group for ACGS-2 MSK"
  vpc_id      = var.vpc_id

  # Kafka broker ports
  ingress {
    description     = "Kafka plaintext"
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    security_groups = var.security_group_ids
  }

  ingress {
    description     = "Kafka TLS"
    from_port       = 9094
    to_port         = 9094
    protocol        = "tcp"
    security_groups = var.security_group_ids
  }

  ingress {
    description     = "Kafka SASL/SCRAM"
    from_port       = 9096
    to_port         = 9096
    protocol        = "tcp"
    security_groups = var.security_group_ids
  }

  # Zookeeper
  ingress {
    description     = "Zookeeper"
    from_port       = 2181
    to_port         = 2181
    protocol        = "tcp"
    security_groups = var.security_group_ids
  }

  # Inter-broker communication
  ingress {
    description = "Inter-broker"
    from_port   = 9092
    to_port     = 9096
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-sg"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.cluster_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# MSK Configuration
resource "aws_msk_configuration" "main" {
  name              = "${var.cluster_name}-config"
  kafka_versions    = [var.kafka_version]
  description       = "ACGS-2 MSK configuration"

  server_properties = <<EOF
auto.create.topics.enable=false
default.replication.factor=3
min.insync.replicas=2
num.io.threads=8
num.network.threads=5
num.partitions=3
num.replica.fetchers=2
replica.lag.time.max.ms=30000
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
socket.send.buffer.bytes=102400
unclean.leader.election.enable=false
zookeeper.session.timeout.ms=18000
log.retention.hours=168
log.segment.bytes=1073741824
message.max.bytes=10485760
EOF
}

# MSK Cluster
resource "aws_msk_cluster" "main" {
  cluster_name           = var.cluster_name
  kafka_version          = var.kafka_version
  number_of_broker_nodes = var.broker_count

  broker_node_group_info {
    instance_type   = var.instance_type
    client_subnets  = var.subnet_ids
    security_groups = [aws_security_group.msk.id]

    storage_info {
      ebs_storage_info {
        volume_size = var.ebs_volume_size
        provisioned_throughput {
          enabled           = var.provisioned_throughput_enabled
          volume_throughput = var.volume_throughput
        }
      }
    }

    connectivity_info {
      public_access {
        type = "DISABLED"
      }
    }
  }

  configuration_info {
    arn      = aws_msk_configuration.main.arn
    revision = aws_msk_configuration.main.latest_revision
  }

  encryption_info {
    encryption_in_transit {
      client_broker = var.encryption_in_transit_client_broker
      in_cluster    = true
    }
    encryption_at_rest_kms_key_arn = var.encryption_at_rest_kms_key_arn
  }

  client_authentication {
    sasl {
      scram = true
      iam   = true
    }
    tls {
      certificate_authority_arns = var.certificate_authority_arns
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }

  open_monitoring {
    prometheus {
      jmx_exporter {
        enabled_in_broker = true
      }
      node_exporter {
        enabled_in_broker = true
      }
    }
  }

  enhanced_monitoring = var.enhanced_monitoring

  tags = merge(var.tags, {
    "acgs.io/constitutional-hash" = local.constitutional_hash
  })
}

# SCRAM Secret
resource "aws_secretsmanager_secret" "msk_scram" {
  count = var.create_scram_secret ? 1 : 0

  name       = "AmazonMSK_${var.cluster_name}_scram"
  kms_key_id = var.encryption_at_rest_kms_key_arn

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "msk_scram" {
  count = var.create_scram_secret ? 1 : 0

  secret_id = aws_secretsmanager_secret.msk_scram[0].id
  secret_string = jsonencode({
    username = var.scram_username
    password = var.scram_password
  })
}

resource "aws_msk_scram_secret_association" "main" {
  count = var.create_scram_secret ? 1 : 0

  cluster_arn     = aws_msk_cluster.main.arn
  secret_arn_list = [aws_secretsmanager_secret.msk_scram[0].arn]

  depends_on = [aws_secretsmanager_secret_version.msk_scram]
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.cluster_name}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CpuUser"
  namespace           = "AWS/Kafka"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "MSK CPU utilization is high"

  dimensions = {
    "Cluster Name" = var.cluster_name
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.alarm_actions

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "disk" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.cluster_name}-disk-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "KafkaDataLogsDiskUsed"
  namespace           = "AWS/Kafka"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "MSK disk utilization is high"

  dimensions = {
    "Cluster Name" = var.cluster_name
  }

  alarm_actions = var.alarm_actions
  ok_actions    = var.alarm_actions

  tags = var.tags
}

# Outputs
output "arn" {
  description = "MSK cluster ARN"
  value       = aws_msk_cluster.main.arn
}

output "bootstrap_brokers" {
  description = "Plaintext bootstrap brokers"
  value       = aws_msk_cluster.main.bootstrap_brokers
}

output "bootstrap_brokers_tls" {
  description = "TLS bootstrap brokers"
  value       = aws_msk_cluster.main.bootstrap_brokers_tls
}

output "bootstrap_brokers_sasl_scram" {
  description = "SASL/SCRAM bootstrap brokers"
  value       = aws_msk_cluster.main.bootstrap_brokers_sasl_scram
}

output "bootstrap_brokers_sasl_iam" {
  description = "IAM bootstrap brokers"
  value       = aws_msk_cluster.main.bootstrap_brokers_sasl_iam
}

output "zookeeper_connect_string" {
  description = "Zookeeper connection string"
  value       = aws_msk_cluster.main.zookeeper_connect_string
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.msk.id
}
