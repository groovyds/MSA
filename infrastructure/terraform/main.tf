provider "aws" {
  region = var.aws_region
}

# EC2 Instance
resource "aws_instance" "app_server" {
  ami           = var.ami_id
  instance_type = "t2.medium"
  key_name      = aws_key_pair.deployer.key_name

  vpc_security_group_ids = [aws_security_group.app_sg.id]
  subnet_id              = aws_subnet.public.id

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = file("${path.module}/scripts/setup_ec2.sh")

  tags = {
    Name = "marketing-strategist-ai"
  }
}

# Security Group
resource "aws_security_group" "app_sg" {
  name        = "marketing-strategist-ai-sg"
  description = "Security group for Marketing Strategist AI application"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
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

# RDS Instance
resource "aws_db_instance" "postgres" {
  identifier           = "marketing-strategist-ai-db"
  engine              = "postgres"
  engine_version      = "15.3"
  instance_class      = "db.t3.medium"
  allocated_storage   = 20
  storage_type        = "gp3"
  
  db_name             = var.db_name
  username            = var.db_username
  password            = var.db_password
  
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.db_subnet.name
  
  skip_final_snapshot    = true
  publicly_accessible    = false
}

# Security Group for RDS
resource "aws_security_group" "db_sg" {
  name        = "marketing-strategist-ai-db-sg"
  description = "Security group for PostgreSQL database"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  
  tags = {
    Name = "marketing-strategist-ai-vpc"
  }
}

# Subnets
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"
  
  tags = {
    Name = "marketing-strategist-ai-public"
  }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"
  
  tags = {
    Name = "marketing-strategist-ai-private"
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "db_subnet" {
  name       = "marketing-strategist-ai-db-subnet"
  subnet_ids = [aws_subnet.private.id]
}

# SSH Key Pair
resource "aws_key_pair" "deployer" {
  key_name   = "marketing-strategist-ai-key"
  public_key = file("${path.module}/keys/id_rsa.pub")
} 