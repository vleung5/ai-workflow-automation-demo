#!/bin/bash

# AWS ECS Infrastructure Setup Script
set -e

ENV=${1:-stage}
REGION=${2:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Setting up AWS ECS infrastructure for environment: $ENV"
echo "Region: $REGION"
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Create ECR repository
ECR_REPO_NAME="ai-workflow-automation-${ENV}"
echo "📦 Creating ECR repository: $ECR_REPO_NAME"

aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $REGION \
  --image-tag-mutability MUTABLE \
  --image-scanning-configuration scanOnPush=true \
  2>/dev/null || echo "Repository already exists"

# Enable ECR lifecycle policy
echo "🔄 Setting ECR lifecycle policy..."
aws ecr put-lifecycle-policy \
  --repository-name $ECR_REPO_NAME \
  --lifecycle-policy-text '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 10 images",
        "selection": {
          "tagStatus": "any",
          "countType": "imageCountMoreThan",
          "countNumber": 10
        },
        "action": {
          "type": "expire"
        }
      }
    ]
  }' \
  --region $REGION 2>/dev/null || echo "Lifecycle policy already exists"

# Create CloudWatch Log Group
LOG_GROUP="/ecs/ai-workflow-automation-${ENV}"
echo "�� Creating CloudWatch Log Group: $LOG_GROUP"

aws logs create-log-group \
  --log-group-name $LOG_GROUP \
  --region $REGION \
  2>/dev/null || echo "Log group already exists"

# Set retention policy
RETENTION=$([[ $ENV == "prod" ]] && echo "30" || echo "7")
aws logs put-retention-policy \
  --log-group-name $LOG_GROUP \
  --retention-in-days $RETENTION \
  --region $REGION 2>/dev/null || echo "Retention policy already set"

# Create ECS Cluster
CLUSTER_NAME="ai-workflow-automation-${ENV}"
echo "🎯 Creating ECS Cluster: $CLUSTER_NAME"

aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --region $REGION \
  --settings name=containerInsights,value=enabled \
  2>/dev/null || echo "Cluster already exists"

# Create IAM roles
TASK_EXEC_ROLE_NAME="ecsTaskExecutionRole-ai-workflow-${ENV}"
TASK_ROLE_NAME="ecsTaskRole-ai-workflow-${ENV}"

echo "🔐 Creating IAM roles..."

# Task Execution Role
aws iam create-role \
  --role-name $TASK_EXEC_ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ecs-tasks.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' \
  2>/dev/null || echo "Task execution role already exists"

aws iam attach-role-policy \
  --role-name $TASK_EXEC_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Task Role
aws iam create-role \
  --role-name $TASK_ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ecs-tasks.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' \
  2>/dev/null || echo "Task role already exists"

# Attach Secrets Manager policy
aws iam put-role-policy \
  --role-name $TASK_ROLE_NAME \
  --policy-name secrets-manager-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        "Resource": "arn:aws:secretsmanager:*:*:secret:ai-workflow-automation/*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:*:*:*"
      }
    ]
  }' 2>/dev/null || echo "Policy already attached"

# Create Secrets Manager secrets
SECRET_NAME="ai-workflow-automation/${ENV}/secrets"
echo "🔑 Creating Secrets Manager secret: $SECRET_NAME"

SECRET_EXISTS=$(aws secretsmanager describe-secret \
  --secret-id $SECRET_NAME \
  --region $REGION \
  2>/dev/null || echo "")

if [ -z "$SECRET_EXISTS" ]; then
  aws secretsmanager create-secret \
    --name $SECRET_NAME \
    --region $REGION \
    --secret-string '{
      "database_url": "postgresql://user:password@host:5432/db",
      "api_key": "your-api-key-here",
      "secret_key": "your-secret-key-here"
    }' 2>/dev/null
  echo "✅ Secret created"
else
  echo "Secret already exists"
fi

echo ""
echo "✨ AWS ECS infrastructure setup complete!"
echo ""
echo "📝 Important Information:"
echo "- ECR Repository: $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME"
echo "- ECS Cluster: $CLUSTER_NAME"
echo "- Task Execution Role: arn:aws:iam::$AWS_ACCOUNT_ID:role/$TASK_EXEC_ROLE_NAME"
echo "- Task Role: arn:aws:iam::$AWS_ACCOUNT_ID:role/$TASK_ROLE_NAME"
echo "- CloudWatch Log Group: $LOG_GROUP"
echo "- Secrets Manager: $SECRET_NAME"
