provider "aws" {
  region = "us-east-1"
}

# Look up default VPC
data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "pushgateway_sg" {
  name        = "pushgateway-sg"
  description = "Allow SSH and HTTP"
  vpc_id      = data.aws_vpc.default.id

  lifecycle {
    prevent_destroy = true
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Pushgateway"
    from_port   = 9091
    to_port     = 9091
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Prometheus"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


# EC2 instance
resource "aws_instance" "pushgateway" {
  ami           = "ami-08c40ec9ead489470" # Ubuntu 22.04 LTS in us-east-1
  instance_type = "t2.micro"
  key_name      = "qa-key"

  vpc_security_group_ids = [aws_security_group.pushgateway_sg.id]

  tags = {
    Name = "Pushgateway-Server"
  }
}
