#!/usr/bin/env bash
# ==========================================================================
# CATT Data Warehouse — AWS Infrastructure Setup
#
# Creates: S3 bucket, IAM role, Redshift Serverless, Glue jobs + triggers
# Requires: AWS CLI v2 configured with admin access
# ==========================================================================

set -euo pipefail

REGION="${AWS_REGION:-us-west-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="${S3_BUCKET_NAME:-catt-pipeline-data}"
GLUE_ROLE_NAME="CattGlueRole"
REDSHIFT_NAMESPACE="catt-namespace"
REDSHIFT_WORKGROUP="catt-workgroup"
REDSHIFT_DB="dev"
REDSHIFT_ADMIN_USER="${REDSHIFT_ADMIN_USER:-cattadmin}"

echo "Account: $ACCOUNT_ID | Region: $REGION"
echo "=================================================="

# --------------------------------------------------------------------------
# S3 Bucket
# --------------------------------------------------------------------------
echo "[1/5] S3 bucket: $S3_BUCKET"

if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo "  Bucket already exists — skipping"
else
    aws s3api create-bucket \
        --bucket "$S3_BUCKET" \
        --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION"
    echo "  Created"
fi

# --------------------------------------------------------------------------
# IAM Role for Glue
# --------------------------------------------------------------------------
echo "[2/5] IAM role: $GLUE_ROLE_NAME"

TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "glue.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

if aws iam get-role --role-name "$GLUE_ROLE_NAME" &>/dev/null; then
    echo "  Role already exists — skipping creation"
else
    aws iam create-role \
        --role-name "$GLUE_ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "Glue role for CATT pipeline - S3 and Redshift access"
    echo "  Created role"
fi

# Attach managed policies
for POLICY in \
    arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole \
    arn:aws:iam::aws:policy/AmazonS3FullAccess \
    arn:aws:iam::aws:policy/AmazonRedshiftFullAccess; do
    aws iam attach-role-policy --role-name "$GLUE_ROLE_NAME" --policy-arn "$POLICY" 2>/dev/null || true
done
echo "  Policies attached"

# Wait for role propagation
sleep 10

# --------------------------------------------------------------------------
# Redshift Serverless
# --------------------------------------------------------------------------
echo "[3/5] Redshift Serverless"

if aws redshift-serverless get-namespace --namespace-name "$REDSHIFT_NAMESPACE" &>/dev/null; then
    echo "  Namespace '$REDSHIFT_NAMESPACE' already exists"
else
    echo "  Creating namespace..."
    aws redshift-serverless create-namespace \
        --namespace-name "$REDSHIFT_NAMESPACE" \
        --db-name "$REDSHIFT_DB" \
        --admin-username "$REDSHIFT_ADMIN_USER" \
        --manage-admin-password \
        --region "$REGION"
    echo "  Namespace created (admin password managed by AWS Secrets Manager)"
fi

if aws redshift-serverless get-workgroup --workgroup-name "$REDSHIFT_WORKGROUP" &>/dev/null; then
    echo "  Workgroup '$REDSHIFT_WORKGROUP' already exists"
else
    echo "  Creating workgroup..."
    aws redshift-serverless create-workgroup \
        --workgroup-name "$REDSHIFT_WORKGROUP" \
        --namespace-name "$REDSHIFT_NAMESPACE" \
        --base-capacity 8 \
        --publicly-accessible \
        --region "$REGION"
    echo "  Workgroup created (8 RPU base capacity, publicly accessible)"
fi

# --------------------------------------------------------------------------
# Glue Connection to Redshift
# --------------------------------------------------------------------------
echo "[4/5] Glue connection + jobs"

REDSHIFT_ENDPOINT=$(aws redshift-serverless get-workgroup \
    --workgroup-name "$REDSHIFT_WORKGROUP" \
    --query 'workgroup.endpoint.address' --output text 2>/dev/null || echo "pending")

echo "  Redshift endpoint: $REDSHIFT_ENDPOINT"

# Create Glue connection (JDBC) — requires endpoint to be available
if [ "$REDSHIFT_ENDPOINT" != "pending" ] && [ "$REDSHIFT_ENDPOINT" != "None" ]; then
    CONN_EXISTS=$(aws glue get-connection --name "catt-redshift" 2>/dev/null && echo "yes" || echo "no")
    if [ "$CONN_EXISTS" = "no" ]; then
        aws glue create-connection --connection-input "{
            \"Name\": \"catt-redshift\",
            \"ConnectionType\": \"JDBC\",
            \"ConnectionProperties\": {
                \"JDBC_CONNECTION_URL\": \"jdbc:redshift://${REDSHIFT_ENDPOINT}:5439/${REDSHIFT_DB}\",
                \"USERNAME\": \"${REDSHIFT_ADMIN_USER}\",
                \"PASSWORD\": \"REPLACE_WITH_SECRET\"
            }
        }" --region "$REGION"
        echo "  Created Glue connection (update PASSWORD from Secrets Manager)"
    else
        echo "  Connection 'catt-redshift' already exists"
    fi
fi

# Upload Glue scripts to S3
echo "  Uploading Glue scripts to S3..."
aws s3 cp glue/transform-episodes.py "s3://${S3_BUCKET}/glue-scripts/transform-episodes.py"
aws s3 cp glue/transform-catt-times.py "s3://${S3_BUCKET}/glue-scripts/transform-catt-times.py"
aws s3 cp glue/transform-narratives.py "s3://${S3_BUCKET}/glue-scripts/transform-narratives.py"
echo "  Scripts uploaded"

# Create Glue jobs
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${GLUE_ROLE_NAME}"
TODAY=$(date +%Y-%m-%d)

for JOB_INFO in \
    "catt-transform-episodes:transform-episodes.py" \
    "catt-transform-catt-times:transform-catt-times.py" \
    "catt-transform-narratives:transform-narratives.py"; do

    JOB_NAME="${JOB_INFO%%:*}"
    SCRIPT="${JOB_INFO##*:}"

    if aws glue get-job --job-name "$JOB_NAME" &>/dev/null; then
        echo "  Job '$JOB_NAME' already exists — updating"
        aws glue update-job --job-name "$JOB_NAME" --job-update "{
            \"Role\": \"${ROLE_ARN}\",
            \"Command\": {
                \"Name\": \"glueetl\",
                \"ScriptLocation\": \"s3://${S3_BUCKET}/glue-scripts/${SCRIPT}\",
                \"PythonVersion\": \"3\"
            },
            \"DefaultArguments\": {
                \"--S3_RAW_PATH\": \"s3://${S3_BUCKET}/catt-pipeline/raw/${TODAY}/\",
                \"--REDSHIFT_CONNECTION\": \"catt-redshift\",
                \"--TempDir\": \"s3://${S3_BUCKET}/glue-tmp/\"
            },
            \"GlueVersion\": \"4.0\",
            \"NumberOfWorkers\": 2,
            \"WorkerType\": \"G.1X\",
            \"Connections\": {\"Connections\": [\"catt-redshift\"]}
        }" --region "$REGION"
    else
        aws glue create-job --name "$JOB_NAME" \
            --role "$ROLE_ARN" \
            --command "{
                \"Name\": \"glueetl\",
                \"ScriptLocation\": \"s3://${S3_BUCKET}/glue-scripts/${SCRIPT}\",
                \"PythonVersion\": \"3\"
            }" \
            --default-arguments "{
                \"--S3_RAW_PATH\": \"s3://${S3_BUCKET}/catt-pipeline/raw/${TODAY}/\",
                \"--REDSHIFT_CONNECTION\": \"catt-redshift\",
                \"--TempDir\": \"s3://${S3_BUCKET}/glue-tmp/\"
            }" \
            --glue-version "4.0" \
            --number-of-workers 2 \
            --worker-type "G.1X" \
            --connections "{\"Connections\": [\"catt-redshift\"]}" \
            --region "$REGION"
        echo "  Created job: $JOB_NAME"
    fi
done

# --------------------------------------------------------------------------
# Glue Triggers — daily schedule
# --------------------------------------------------------------------------
echo "[5/5] Glue daily triggers"

for JOB_INFO in \
    "catt-daily-episodes:catt-transform-episodes" \
    "catt-daily-catt-times:catt-transform-catt-times" \
    "catt-daily-narratives:catt-transform-narratives"; do

    TRIGGER_NAME="${JOB_INFO%%:*}"
    JOB_NAME="${JOB_INFO##*:}"

    if aws glue get-trigger --name "$TRIGGER_NAME" &>/dev/null; then
        echo "  Trigger '$TRIGGER_NAME' already exists"
    else
        aws glue create-trigger \
            --name "$TRIGGER_NAME" \
            --type SCHEDULED \
            --schedule "cron(0 7 * * ? *)" \
            --actions "[{\"JobName\": \"${JOB_NAME}\"}]" \
            --start-on-creation \
            --region "$REGION"
        echo "  Created trigger: $TRIGGER_NAME (daily at 7:00 UTC)"
    fi
done

echo ""
echo "=================================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Retrieve Redshift admin password from AWS Secrets Manager"
echo "  2. Update the Glue connection 'catt-redshift' with the real password"
echo "  3. Run redshift/schema.sql against Redshift to create tables"
echo "  4. Run: npm run extract  (to populate S3 with raw data)"
echo "  5. Manually trigger Glue jobs or wait for daily schedule"
echo "=================================================="
