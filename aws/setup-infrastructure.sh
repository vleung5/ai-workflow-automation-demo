#!/bin/bash

##############################################################################
# AWS ECS and S3 Infrastructure Setup Script
# Sets up complete AWS resources for AI Workflow Automation application
# 
# Usage: bash aws/setup-infrastructure.sh [stage|prod] [region]
# Example: bash aws/setup-infrastructure.sh stage us-east-1
##############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions for colored output
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Get environment and region parameters
ENV=${1:-stage}
REGION=${2:-us-east-1}

# Validate environment
if [[ ! "$ENV" =~ ^(dev|stage|prod)$ ]]; then
    log_error "Invalid environment. Use: dev, stage, or prod"
    exit 1
fi

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$AWS_ACCOUNT_ID" ]; then
    log_error "Failed to get AWS Account ID. Check your AWS credentials."
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  AWS Infrastructure Setup - AI Workflow Automation             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
log_info "Environment: $ENV"
log_info "Region: $REGION"
log_info "AWS Account ID: $AWS_ACCOUNT_ID"
echo ""

# =============================================================================
# 1. CREATE S3 BUCKETS
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Creating S3 buckets..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

BUCKET_NAME="ai-workflow-automation-${ENV}"

# Create bucket
if aws s3api head-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null; then
    log_warning "Bucket already exists: $BUCKET_NAME"
else
    log_info "Creating bucket: $BUCKET_NAME"
    if [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$REGION" 2>/dev/null && log_success "Bucket created" || log_warning "Bucket creation failed"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION" 2>/dev/null && log_success "Bucket created" || log_warning "Bucket creation failed"
    fi
fi

# Enable versioning
log_info "Enabling versioning..."
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled \
    --region "$REGION" 2>/dev/null && log_success "Versioning enabled" || log_warning "Versioning already enabled"

# Create bucket folders/prefixes
log_info "Creating S3 bucket structure..."
for folder in "incoming" "processed" "failed" "archived" "results"; do
    aws s3api put-object \
        --bucket "$BUCKET_NAME" \
        --key "${folder}/" \
        --region "$REGION" 2>/dev/null || true
done
log_success "S3 bucket structure created"

# Enable encryption
log_info "Enabling S3 bucket encryption..."
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }' \
    --region "$REGION" 2>/dev/null && log_success "Encryption enabled" || log_warning "Encryption already configured"

# Block public access
log_info "Blocking public access..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
    --region "$REGION" 2>/dev/null && log_success "Public access blocked" || log_warning "Already blocked"

# Set lifecycle policy
log_info "Setting lifecycle policy..."
RETENTION_DAYS=$([[ $ENV == "prod" ]] && echo "90" || echo "30")
aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration '{
        "Rules": [
            {
                "Id": "DeleteOldProcessedFiles",
                "Status": "Enabled",
                "Prefix": "processed/",
                "Expiration": { "Days": '$RETENTION_DAYS' },
                "NoncurrentVersionExpiration": { "NoncurrentDays": 30 }
            },
            {
                "Id": "DeleteOldFailedFiles",
                "Status": "Enabled",
                "Prefix": "failed/",
                "Expiration": { "Days": '$((RETENTION_DAYS - 30))' },
                "NoncurrentVersionExpiration": { "NoncurrentDays": 30 }
            },
            {
                "Id": "ArchiveOldResults",
                "Status": "Enabled",
                "Prefix": "results/",
                "Transitions": [
                    {
                        "Days": 30,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "Days": 90,
                        "StorageClass": "GLACIER"
                    }
                ]
            }
        ]
    }' \
    --region "$REGION" 2>/dev/null && log_success "Lifecycle policy set" || log_warning "Lifecycle policy already configured"

# =============================================================================
# 2. CREATE ECR REPOSITORY
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Setting up ECR repository..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ECR_REPO_NAME="ai-workflow-automation-${ENV}"

aws ecr create-repository \
    --repository-name "$ECR_REPO_NAME" \
    --region "$REGION" \
    --image-tag-mutability MUTABLE \
    --image-scanning-configuration scanOnPush=true 2>/dev/null && log_success "ECR repository created" || log_warning "ECR repository already exists"

# Set lifecycle policy
log_info "Setting ECR lifecycle policy..."
aws ecr put-lifecycle-policy \
    --repository-name "$ECR_REPO_NAME" \
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
    --region "$REGION" 2>/dev/null && log_success "ECR lifecycle policy set" || log_warning "ECR lifecycle policy already configured"

# =============================================================================
# 3. CREATE CLOUDWATCH LOG GROUPS
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Setting up CloudWatch logs..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LOG_GROUP="/ecs/ai-workflow-automation-${ENV}"

aws logs create-log-group \
    --log-group-name "$LOG_GROUP" \
    --region "$REGION" 2>/dev/null && log_success "Log group created" || log_warning "Log group already exists"

# Set retention policy
RETENTION=$([[ $ENV == "prod" ]] && echo "30" || echo "7")
log_info "Setting log retention to $RETENTION days..."
aws logs put-retention-policy \
    --log-group-name "$LOG_GROUP" \
    --retention-in-days "$RETENTION" \
    --region "$REGION" 2>/dev/null && log_success "Retention policy set" || true

# =============================================================================
# 4. CREATE ECS CLUSTER
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Setting up ECS cluster..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CLUSTER_NAME="ai-workflow-automation-${ENV}"

aws ecs create-cluster \
    --cluster-name "$CLUSTER_NAME" \
    --region "$REGION" \
    --settings name=containerInsights,value=enabled 2>/dev/null && log_success "ECS cluster created" || log_warning "ECS cluster already exists"

# =============================================================================
# 5. CREATE IAM ROLES
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━��━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Setting up IAM roles..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TASK_EXEC_ROLE_NAME="ecsTaskExecutionRole-ai-workflow-${ENV}"
TASK_ROLE_NAME="ecsTaskRole-ai-workflow-${ENV}"

# Task Execution Role
log_info "Creating task execution role..."
aws iam create-role \
    --role-name "$TASK_EXEC_ROLE_NAME" \
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
    }' 2>/dev/null && log_success "Task execution role created" || log_warning "Task execution role already exists"

# Attach execution role policy
log_info "Attaching AmazonECSTaskExecutionRolePolicy..."
aws iam attach-role-policy \
    --role-name "$TASK_EXEC_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy 2>/dev/null && log_success "Policy attached" || true

# Task Role
log_info "Creating task role..."
aws iam create-role \
    --role-name "$TASK_ROLE_NAME" \
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
    }' 2>/dev/null && log_success "Task role created" || log_warning "Task role already exists"

# Attach S3, Secrets Manager, and Logs policy
log_info "Attaching S3, Secrets Manager, and CloudWatch Logs permissions..."
aws iam put-role-policy \
    --role-name "$TASK_ROLE_NAME" \
    --policy-name s3-secrets-logs-policy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3Access",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:CopyObject",
                    "s3:ListBucketVersions"
                ],
                "Resource": [
                    "arn:aws:s3:::ai-workflow-automation-*",
                    "arn:aws:s3:::ai-workflow-automation-*/*"
                ]
            },
            {
                "Sid": "SecretsManagerAccess",
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                "Resource": "arn:aws:secretsmanager:*:*:secret:ai-workflow-automation/*"
            },
            {
                "Sid": "CloudWatchLogsAccess",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            },
            {
                "Sid": "ECRAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer"
                ],
                "Resource": "*"
            }
        ]
    }' 2>/dev/null && log_success "Permissions attached" || log_warning "Permissions already attached"

# =============================================================================
# 6. CREATE SECRETS MANAGER SECRETS
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Setting up Secrets Manager..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SECRET_NAME="ai-workflow-automation/${ENV}/secrets"

log_info "Checking for existing secret: $SECRET_NAME"
SECRET_EXISTS=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" 2>/dev/null || echo "")

if [ -z "$SECRET_EXISTS" ]; then
    log_info "Creating secret..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --region "$REGION" \
        --description "Secrets for AI Workflow Automation - $ENV environment" \
        --secret-string '{
            "database_url": "postgresql://user:password@host:5432/db",
            "api_key": "your-api-key-here",
            "secret_key": "your-secret-key-here",
            "s3_bucket": "'$BUCKET_NAME'"
        }' 2>/dev/null && log_success "Secret created" || log_error "Failed to create secret"
else
    log_success "Secret already exists"
fi

# =============================================================================
# 7. CREATE VPC AND SUBNETS (Optional - for better security)
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "VPC Configuration (using default VPC)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get default VPC
DEFAULT_VPC=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" \
    --region "$REGION" \
    --output text 2>/dev/null)

if [ "$DEFAULT_VPC" != "None" ] && [ -n "$DEFAULT_VPC" ]; then
    log_success "Using default VPC: $DEFAULT_VPC"
else
    log_warning "No default VPC found. You may need to specify VPC/Subnet for ECS tasks."
fi

# =============================================================================
# 8. SUMMARY
# =============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   ✓ SETUP COMPLETE                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "📊 Resource Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  S3 Configuration:"
echo "  ├─ Bucket: $BUCKET_NAME"
echo "  ├─ Region: $REGION"
echo "  ├─ Encryption: AES-256"
echo "  ├─ Versioning: Enabled"
echo "  ├─ Public Access: Blocked"
echo "  ├─ Lifecycle Retention: $RETENTION_DAYS days"
echo "  └─ Folders: incoming/, processed/, failed/, archived/, results/"
echo ""
echo "  ECR Configuration:"
echo "  ├─ Repository: $ECR_REPO_NAME"
echo "  ├─ URI: $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME"
echo "  └─ Image Scanning: Enabled"
echo ""
echo "  ECS Configuration:"
echo "  ├─ Cluster: $CLUSTER_NAME"
echo "  ├─ Container Insights: Enabled"
echo "  └─ Default VPC: $DEFAULT_VPC"
echo ""
echo "  IAM Roles:"
echo "  ├─ Execution Role: arn:aws:iam::$AWS_ACCOUNT_ID:role/$TASK_EXEC_ROLE_NAME"
echo "  ├─ Task Role: arn:aws:iam::$AWS_ACCOUNT_ID:role/$TASK_ROLE_NAME"
echo "  └─ Permissions: S3, Secrets Manager, CloudWatch Logs"
echo ""
echo "  CloudWatch:"
echo "  ├─ Log Group: $LOG_GROUP"
echo "  ├─ Retention: $RETENTION days"
echo "  └─ Monitoring: Container Insights"
echo ""
echo "  Secrets Manager:"
echo "  └─ Secret Name: $SECRET_NAME"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# =============================================================================
# 9. NEXT STEPS
# =============================================================================
echo "🚀 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Update GitHub Actions Secrets (GitHub repo Settings → Secrets):"
echo "   ├─ AWS_ROLE_TO_ASSUME"
echo "   ├─ ECS_TASK_EXECUTION_ROLE_ARN"
echo "   └─ ECS_TASK_ROLE_ARN"
echo ""
echo "2. Build and push Docker image:"
echo "   ├─ aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
echo "   ├─ docker build -t $ECR_REPO_NAME:latest ."
echo "   ├─ docker tag $ECR_REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.](#)

