# Terraform stub for the claim-events Kafka cluster.

resource "aws_msk_cluster" "claim_events" {
  cluster_name           = "pbm-claim-events"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = 6

  broker_node_group_info {
    instance_type   = "kafka.m5.large"
    client_subnets  = var.subnet_ids
    security_groups = [aws_security_group.kafka.id]
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.kafka.arn

    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  configuration_info {
    arn      = aws_msk_configuration.claim_events.arn
    revision = aws_msk_configuration.claim_events.latest_revision
  }
}

resource "aws_kms_key" "kafka" {
  description             = "Customer-managed KMS key for claim-events MSK cluster"
  enable_key_rotation     = false   # NOTE: rotation not enabled per current config
  deletion_window_in_days = 30
}
