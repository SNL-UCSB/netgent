# Copyright 2016-2018, Pulumi Corporation.  All rights reserved.

import pulumi
import pulumi_aws as aws
import pulumi_docker as docker
import json

# Configurations
container_context = "."
container_file = "Dockerfile"
region = aws.get_region().region
current = aws.get_caller_identity_output()
pulumi_stack = pulumi.get_stack()
account_id = current.account_id


# == Docker Container ==
# ECR (Elastic Container Registry) Repository
ecr_repository = aws.ecr.Repository(
    "ecr-repository",
    name=f"netgent-infra-{pulumi_stack}",
    force_delete=True,
)
# ECR (Elastic Container Registry) Lifecycle Policy (Delete images when they are more than 10 available)
token = aws.ecr.get_authorization_token_output(registry_id=ecr_repository.registry_id)
ecr_life_cycle_policy = aws.ecr.LifecyclePolicy(
    "ecr-life-cycle-policy",
    repository=ecr_repository.name,
    policy=json.dumps(
        {
            "rules": [
                {
                    "rulePriority": 1,
                    "description": "Expire images when they are more than 10 available",
                    "selection": {
                        "tagStatus": "any",
                        "countType": "imageCountMoreThan",
                        "countNumber": 10,
                    },
                    "action": {
                        "type": "expire",
                    },
                }
            ],
        }
    ),
)

# Builds the Docker Image and Pushes to ECR (Elastic Container Registry)
ecr_image = docker.Image(
    "ecr-image",
    build=docker.DockerBuildArgs(
        platform="linux/amd64",
        context=container_context,
        dockerfile=container_file,
    ),
    image_name=ecr_repository.repository_url,
    registry=docker.RegistryArgs(
        server=ecr_repository.repository_url,
        username=token.user_name,
        password=pulumi.Output.secret(token.password),
    ),
)

# == EC2 Instance ==
# EC2 Instance Size
size = "t2.small"

# Get Amazon Linux 2 AMI (stable and well-supported)
ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["amazon"],
    filters=[
        {"name": "name", "values": ["amzn2-ami-hvm-*-x86_64-gp2"]},
        {"name": "virtualization-type", "values": ["hvm"]},
    ],
)

# Security Group for EC2 Instance (Flask API)
group = aws.ec2.SecurityGroup(
    "flask-api-secgrp",
    description="Enable HTTP access for Flask API",
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 8080,
            "to_port": 8080,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "Flask API port",
        },
        {
            "protocol": "tcp",
            "from_port": 22,
            "to_port": 22,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "SSH access",
        },
    ],
    egress=[
        {
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "Allow all outbound traffic",
        }
    ],
    tags={
        "Name": "flask-api-security-group",
    },
)

# User data script to install Docker, authenticate to ECR, and run the container from ECR
# Use apply to properly handle Pulumi Outputs in the user_data string
user_data = pulumi.Output.all(ecr_repository.repository_url, region).apply(
    lambda args: f"""#!/bin/bash
set -e

# Update system
sudo yum update -y

# Install Docker and AWS CLI
sudo yum install -y docker git awscli

# Start and enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

sudo usermod -a -G docker ec2-user

# Authenticate to ECR
sudo aws ecr get-login-password --region {args[1]} | sudo docker login --username AWS --password-stdin {args[0].split('/')[0]}

# Pull the container image from ECR
sudo docker pull {args[0]}

# Run the container image
sudo docker run -d \
    --name netgent-app \
    --restart unless-stopped \
    -p 8080:8080 \
    {args[0]}
"""
)

# IAM role for EC2 instance (optional, for accessing other AWS services)
instance_role = aws.iam.Role(
    "ec2-instance-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Effect": "Allow"
            }
        ]
    }""",
    tags={
        "Name": "ec2-instance-role",
        "Project": "netgent",
    },
)

# Attach basic EC2 role policy
aws.iam.RolePolicyAttachment(
    "ec2-instance-role-policy",
    role=instance_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
)

# Instance profile
instance_profile = aws.iam.InstanceProfile(
    "ec2-instance-profile",
    role=instance_role.name,
)

# EC2 Instance
server = aws.ec2.Instance(
    f"flask-api-server-{pulumi_stack}",
    instance_type=size,
    vpc_security_group_ids=[group.id],
    ami=ami.id,
    iam_instance_profile=instance_profile.name,
    user_data=user_data,
    tags={
        "Name": f"netgent-infra-{pulumi_stack}",
        "Project": "netgent",
    },
)

# Export outputs
pulumi.export("public_ip", server.public_ip)
pulumi.export("public_dns", server.public_dns)
pulumi.export("api_url", pulumi.Output.all(server.public_ip).apply(
    lambda args: f"http://{args[0]}:8080"
))
pulumi.export("ecr_repository_url", ecr_repository.repository_url)
pulumi.export("ecr_registry_url", ecr_repository.repository_url.apply(lambda url: url.split('/')[0]))
pulumi.export("region", region)