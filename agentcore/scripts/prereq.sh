#!/bin/sh

# Enable strict error handling
set -euo pipefail

# ----- Config -----
BUCKET_NAME=${1:-customersupport112}
INFRA_STACK_NAME=${2:-CustomerSupportStackInfra}
COGNITO_STACK_NAME=${3:-CustomerSupportStackCognito}
INFRA_TEMPLATE_FILE="prerequisite/infrastructure.yaml"
COGNITO_TEMPLATE_FILE="prerequisite/cognito.yaml"
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")


# Get AWS Account ID with proper error handling
echo "🔍 Getting AWS Account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>&1)
if [ $? -ne 0 ] || [ -z "$ACCOUNT_ID" ] || [ "$ACCOUNT_ID" = "None" ]; then
    echo "❌ Failed to get AWS Account ID. Please check your AWS credentials and network connectivity."
    echo "Error: $ACCOUNT_ID"
    exit 1
fi


FULL_BUCKET_NAME="${BUCKET_NAME}-${ACCOUNT_ID}-${REGION}"
LAMBDA_SRC="prerequisite/lambda/customersupport"

USER_POOL_NAME="CustomerSupportGatewayPool" 
MACHINE_APP_CLIENT_NAME="CustomerSupportMachineClient" 
WEB_APP_CLIENT_NAME="CustomerSupportWebClient"

echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
# ----- 1. Create S3 bucket -----
echo "🪣 Using S3 bucket: $FULL_BUCKET_NAME"
if [ "$REGION" = "us-east-1" ]; then
  aws s3api create-bucket \
    --bucket "$FULL_BUCKET_NAME" \
    2>/dev/null || echo "ℹ️ Bucket may already exist or be owned by you."
else
  aws s3api create-bucket \
    --bucket "$FULL_BUCKET_NAME" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION" \
    2>/dev/null || echo "ℹ️ Bucket may already exist or be owned by you."
fi

# Check architecture and install packages only on ARM
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    echo "Installing dependencies for the Lambda function."
    echo "🔧 ARM architecture detected ($ARCH), installing Python packages..."
    pip install -r "$LAMBDA_SRC/requirements.txt" -t "$LAMBDA_SRC/packages"
else
    echo "You're not running on ARM but we need to package for an ARM Lambda. Installing dependencies via Docker."
    docker run --rm -v "$PWD":/var/task public.ecr.aws/sam/build-python3.13:latest-arm64 \
      pip install -r "$LAMBDA_SRC/requirements.txt" -t "$LAMBDA_SRC/packages"
fi

# ----- Verify S3 bucket ownership -----
echo "🔍 Verifying S3 bucket ownership..."
aws s3api head-bucket --bucket "$FULL_BUCKET_NAME" --expected-bucket-owner "$ACCOUNT_ID"
if [ $? -ne 0 ]; then
    echo "❌ S3 bucket $FULL_BUCKET_NAME is not owned by account $ACCOUNT_ID"
    exit 1
fi
echo "✅ S3 bucket ownership verified"

# ----- 3. Deploy CloudFormation -----
deploy_stack() {
  set +e

  local stack_name=$1
  local template_file=$2
  local packaged_file="$2.packaged"
  shift 2
  local params=("$@")

  echo "🚀 Deploying CloudFormation stack: $stack_name"

  output=$(aws cloudformation package \
    --template-file "$template_file" \
    --s3-bucket "$FULL_BUCKET_NAME" \
    --output-template-file "$packaged_file" 2>&1)

echo "Package: $output"

  output=$(aws cloudformation deploy \
    --tags "app=pace_bootcamp" \
    --stack-name "$stack_name" \
    --template-file "$packaged_file" \
    --s3-bucket "$FULL_BUCKET_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    "${params[@]}" 2>&1)

  exit_code=$?

  echo "Deploy: $output"

  if [ $exit_code -ne 0 ]; then
    if echo "$output" | grep -qi "No changes to deploy"; then
      echo "ℹ️ No updates for stack $stack_name, continuing..."
      return 0
    else
      echo "❌ Error deploying stack $stack_name:"
      echo "$output"
      return $exit_code
    fi
  else
    echo "✅ Stack $stack_name deployed successfully."
    return 0
  fi
}

# ----- Run both stacks -----
echo "🔧 Starting deployment of infrastructure stack with LambdaS3Bucket = $FULL_BUCKET_NAME..."
deploy_stack "$INFRA_STACK_NAME" "$INFRA_TEMPLATE_FILE" --parameter-overrides LambdaS3Bucket="$FULL_BUCKET_NAME"
infra_exit_code=$?

echo "🔧 Starting deployment of Cognito stack..."
deploy_stack "$COGNITO_STACK_NAME" "$COGNITO_TEMPLATE_FILE" --parameter-overrides UserPoolName="$USER_POOL_NAME" MachineAppClientName="$MACHINE_APP_CLIENT_NAME" WebAppClientName="$WEB_APP_CLIENT_NAME"
cognito_exit_code=$?

echo "✅ Deployment complete."
