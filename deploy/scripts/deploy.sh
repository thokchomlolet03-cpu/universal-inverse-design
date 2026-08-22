#!/usr/bin/env bash
# ==============================================================================
# Universal Inverse Design Engine — 1-Click Zero-Cost Serverless Deployment
# Deploys FastAPI container to Google Cloud Run and provisions BigQuery datasets.
# ==============================================================================

set -euo pipefail

PROJECT_ID="${1:-universal-inverse-design}"
REGION="${2:-us-central1}"
IMAGE_TAG="v0.7.0"
IMAGE_URI="gcr.io/${PROJECT_ID}/uid-engine-api:${IMAGE_TAG}"

echo "================================================================="
echo " Deploying UID Engine v0.7.0 to Google Cloud Run (Serverless)"
echo " Project: ${PROJECT_ID} | Region: ${REGION}"
echo "================================================================="

# 1. Verify gcloud CLI authentication
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: 'gcloud' CLI is not installed."
    exit 1
fi

# 2. Build and submit container image via Google Cloud Build
echo ""
echo "📦 Building container image: ${IMAGE_URI}..."
gcloud builds submit --project="${PROJECT_ID}" --tag="${IMAGE_URI}" .

# 3. Apply Terraform infrastructure
echo ""
echo "🏗️ Applying Terraform configuration..."
cd deploy/terraform
terraform init
terraform apply -auto-approve \
    -var="project_id=${PROJECT_ID}" \
    -var="region=${REGION}" \
    -var="container_image=${IMAGE_URI}"

SERVICE_URL=$(terraform output -raw service_url)

echo ""
echo "================================================================="
echo " ✅ Deployment Successful!"
echo " Public API URL: ${SERVICE_URL}"
echo " Health Probe:   ${SERVICE_URL}/health"
echo " Interactive Docs: ${SERVICE_URL}/docs"
echo "================================================================="
