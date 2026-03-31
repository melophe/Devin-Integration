# 最新のAmazon Linux 2023 AMI
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# SSM用IAMロール
resource "aws_iam_role" "ec2_ssm" {
  name = "redmine-devin-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_ssm" {
  name = "redmine-devin-ec2-profile"
  role = aws_iam_role.ec2_ssm.name
}

# EC2インスタンス（Redmine）
resource "aws_instance" "redmine" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.redmine.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_ssm.name

  associate_public_ip_address = true

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y docker git
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ec2-user

    # Docker Compose インストール
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    # Redmine起動
    mkdir -p /opt/redmine
    cat > /opt/redmine/docker-compose.yml <<'COMPOSE'
version: '3'
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: redmine
      MYSQL_DATABASE: redmine
      MYSQL_USER: redmine
      MYSQL_PASSWORD: redmine
    volumes:
      - db_data:/var/lib/mysql
  redmine:
    build:
      context: /opt/redmine
    depends_on:
      - db
    ports:
      - "3000:3000"
    environment:
      REDMINE_DB_MYSQL: db
      REDMINE_DB_PASSWORD: redmine
      REDMINE_DB_USERNAME: redmine
      REDMINE_SECRET_KEY_BASE: supersecretkey
    volumes:
      - redmine_data:/usr/src/redmine/files
volumes:
  db_data:
  redmine_data:
COMPOSE

    cat > /opt/redmine/Dockerfile <<'DOCKERFILE'
FROM redmine:5.1
RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/suer/redmine_webhook /usr/src/redmine/plugins/redmine_webhook
DOCKERFILE

    cd /opt/redmine && docker-compose up -d
    sleep 60
    docker-compose exec -T redmine bundle exec rake redmine:plugins:migrate RAILS_ENV=production
  EOF

  tags = { Name = "redmine-devin-redmine" }
}

output "redmine_url" {
  value = "http://${aws_instance.redmine.public_ip}:3000"
}
