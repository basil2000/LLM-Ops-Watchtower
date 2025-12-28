#!/bin/bash
# Deployment script for LLM Ops Watchtower to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-llm-ops-watchtower}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Validate required environment variables
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT environment variable is not set${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 Deploying LLM Ops Watchtower to Cloud Run${NC}"
echo -e "Project: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "Region: ${YELLOW}${REGION}${NC}"
echo -e "Service: ${YELLOW}${SERVICE_NAME}${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Authenticate and set project
echo -e "${YELLOW}📋 Setting up Google Cloud...${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}🔌 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Build Docker image
echo -e "${YELLOW}🐳 Building Docker image...${NC}"
docker build -t "$IMAGE_NAME" .

# Push to Google Container Registry
echo -e "${YELLOW}📤 Pushing image to GCR...${NC}"
docker push "$IMAGE_NAME"

# Deploy to Cloud Run
echo -e "${YELLOW}☁️  Deploying to Cloud Run...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "VERTEX_LOCATION=${REGION}" \
    --set-env-vars "GEMINI_MODEL=${GEMINI_MODEL:-gemini-1.5-pro}" \
    --set-env-vars "OTEL_SERVICE_NAME=${SERVICE_NAME}" \
    --set-env-vars "DEPLOYMENT_ENVIRONMENT=production"

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "Service URL: ${GREEN}${SERVICE_URL}${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Set environment variables in Cloud Run console or via:"
echo "   gcloud run services update $SERVICE_NAME --region $REGION --update-env-vars KEY=VALUE"
echo "2. Configure Datadog OTLP endpoint and API key"
echo "3. Test the deployment: curl $SERVICE_URL/health"
echo "4. Visit $SERVICE_URL in your browser"

