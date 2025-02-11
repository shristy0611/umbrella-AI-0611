resource "aws_instance" "umbrella_ai" {
  ami           = "ami-0c55b159cbfafe1f0"  # Amazon Linux 2 AMI ID
  instance_type = "t2.micro"
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.umbrella_ai.id]

  root_block_device {
    volume_size = 30
    volume_type = "gp2"
  }

  user_data = file("${path.module}/ec2_setup.sh")

  tags = {
    Name = "umbrella-ai"
    Environment = "production"
  }
}

# Elastic IP for the EC2 instance
resource "aws_eip" "umbrella_ai" {
  instance = aws_instance.umbrella_ai.id
  vpc      = true

  tags = {
    Name = "umbrella-ai-eip"
    Environment = "production"
  }
}

# Output the public IP
output "public_ip" {
  value = aws_eip.umbrella_ai.public_ip
}

# Variables
variable "key_name" {
  description = "Name of the SSH key pair"
  type        = string
} 