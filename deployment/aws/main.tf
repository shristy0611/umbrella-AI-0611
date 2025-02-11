terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"  # Using US East (N. Virginia) region for Free Tier
}

# Import existing configurations
module "ec2" {
  source = "."
  key_name = var.key_name
}

# Variables
variable "key_name" {
  description = "Name of the SSH key pair"
  type        = string
}

# Outputs
output "instance_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = module.ec2.public_ip
}

output "grafana_url" {
  description = "URL for Grafana dashboard"
  value       = "http://${module.ec2.public_ip}:3000"
}

output "prometheus_url" {
  description = "URL for Prometheus"
  value       = "http://${module.ec2.public_ip}:9090"
}

output "jaeger_url" {
  description = "URL for Jaeger UI"
  value       = "http://${module.ec2.public_ip}:16686"
}

# Create an S3 bucket for backups
resource "aws_s3_bucket" "backups" {
  bucket = "umbrella-ai-backups-${random_string.bucket_suffix.result}"
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Enable versioning for the backup bucket
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for the backup bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Create an IAM role for EC2 to access S3
resource "aws_iam_role" "ec2_s3_access" {
  name = "umbrella-ai-ec2-s3-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Attach S3 access policy to the IAM role
resource "aws_iam_role_policy" "s3_access" {
  name = "umbrella-ai-s3-access"
  role = aws_iam_role.ec2_s3_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*"
        ]
      }
    ]
  })
}

# Create an instance profile for the IAM role
resource "aws_iam_instance_profile" "ec2_s3_profile" {
  name = "umbrella-ai-ec2-s3-profile"
  role = aws_iam_role.ec2_s3_access.name
} 