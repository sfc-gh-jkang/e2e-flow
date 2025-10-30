#!/bin/bash

# Snowflake SPCS Deployment Script
# Based on: https://github.com/sfc-gh-jkang/cortex-cost-app-spcs

set -e

# Configuration
SNOWFLAKE_CONNECTION="default"
DATABASE="E2E_FLOW_DB"
IMAGE_SCHEMA="IMAGE_SCHEMA"
APP_SCHEMA="APP_SCHEMA"
IMAGE_REPO="IMAGE_REPO"
COMPUTE_POOL="E2E_FLOW_COMPUTE_POOL"
SERVICE_NAME="E2E_FLOW_SERVICE"
IMAGE_NAME="e2e-flow"
IMAGE_TAG="latest"
APP_STAGE="APP_STAGE"

# Parse command line arguments
UPDATE_MODE=false
LOCAL_MODE=false

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --update          Update existing service (preserves ingress URL)"
    echo "  --local           Run in local development mode"
    echo "  --connection NAME Snowflake CLI connection name (default: default)"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # First deployment (creates new service)"
    echo "  $0 --update       # Update existing service"
    echo "  $0 --local        # Local development mode"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --update)
            UPDATE_MODE=true
            shift
            ;;
        --local)
            LOCAL_MODE=true
            shift
            ;;
        --connection)
            SNOWFLAKE_CONNECTION="$2"
            shift 2
            ;;
        --help)
            print_usage
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            ;;
    esac
done

# Local mode - just build and run
if [ "$LOCAL_MODE" = true ]; then
    echo "🏃 Running in local development mode..."
    docker build --platform linux/amd64 -t ${IMAGE_NAME}:${IMAGE_TAG} .
    echo ""
    echo "✅ Local build complete!"
    echo "Run with: docker run -p 8080:8080 ${IMAGE_NAME}:${IMAGE_TAG}"
    exit 0
fi

# Check if Snowflake CLI is installed
if ! command -v snow &> /dev/null; then
    echo "❌ Error: Snowflake CLI (snow) is not installed"
    echo "Install from: https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation"
    exit 1
fi

# Test connection
echo "🔌 Testing Snowflake connection..."
if ! snow connection test -c "$SNOWFLAKE_CONNECTION" &> /dev/null; then
    echo "❌ Error: Cannot connect to Snowflake using connection '$SNOWFLAKE_CONNECTION'"
    echo "Available connections:"
    snow connection list
    exit 1
fi

echo "✅ Connected to Snowflake"

# Get registry URL
echo "📦 Getting image repository URL..."
REPO_URL=$(snow sql -q "SELECT REPOSITORY_URL FROM ${DATABASE}.INFORMATION_SCHEMA.IMAGE_REPOSITORIES WHERE REPOSITORY_NAME = '${IMAGE_REPO}' AND REPOSITORY_SCHEMA = '${IMAGE_SCHEMA}';" -c "$SNOWFLAKE_CONNECTION" -o json 2>/dev/null | grep -o '"REPOSITORY_URL":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$REPO_URL" ]; then
    echo "❌ Error: Could not find image repository URL"
    echo "Make sure the repository exists: ${DATABASE}.${IMAGE_SCHEMA}.${IMAGE_REPO}"
    exit 1
fi

FULL_IMAGE_PATH="${REPO_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
echo "📍 Target image: ${FULL_IMAGE_PATH}"

# Build Docker image
echo ""
echo "🐳 Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Tag for Snowflake
echo "🏷️  Tagging image..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE_PATH}

# Login to Snowflake registry
echo "🔐 Logging into Snowflake registry..."
REGISTRY_HOSTNAME=$(echo $REPO_URL | cut -d'/' -f1)
snow sql -q "SELECT SYSTEM\$REGISTRY_LOGIN('${REGISTRY_HOSTNAME}');" -c "$SNOWFLAKE_CONNECTION" > /dev/null

# Push image
echo "⬆️  Pushing image to Snowflake..."
docker push ${FULL_IMAGE_PATH}

# Upload service spec
echo "📤 Uploading service specification..."
snow sql -q "PUT file://spcs-service-spec.yaml @${DATABASE}.${APP_SCHEMA}.${APP_STAGE} AUTO_COMPRESS=FALSE OVERWRITE=TRUE;" -c "$SNOWFLAKE_CONNECTION" > /dev/null

if [ "$UPDATE_MODE" = true ]; then
    # Update existing service
    echo ""
    echo "🔄 Updating existing service (preserving ingress URL)..."
    
    # Suspend service
    echo "   Suspending service..."
    snow sql -q "ALTER SERVICE ${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME} SUSPEND;" -c "$SNOWFLAKE_CONNECTION" > /dev/null || true
    
    # Wait a moment for suspension
    sleep 2
    
    # Resume service (pulls new image)
    echo "   Resuming service with new image..."
    snow sql -q "ALTER SERVICE ${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME} RESUME;" -c "$SNOWFLAKE_CONNECTION" > /dev/null
    
    echo "   ✅ Service updated!"
else
    # Create new service
    echo ""
    echo "🆕 Creating new service..."
    
    # Drop existing service if present
    snow sql -q "DROP SERVICE IF EXISTS ${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME};" -c "$SNOWFLAKE_CONNECTION" > /dev/null 2>&1 || true
    
    # Create service
    snow sql -q "CREATE SERVICE ${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME}
        IN COMPUTE POOL ${COMPUTE_POOL}
        FROM @${DATABASE}.${APP_SCHEMA}.${APP_STAGE}
        SPECIFICATION_FILE = 'spcs-service-spec.yaml'
        MIN_INSTANCES = 1
        MAX_INSTANCES = 1;" -c "$SNOWFLAKE_CONNECTION" > /dev/null
    
    echo "   ✅ Service created!"
fi

# Wait for service to be ready
echo ""
echo "⏳ Waiting for service to be ready..."
for i in {1..30}; do
    STATUS=$(snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME}');" -c "$SNOWFLAKE_CONNECTION" -o json 2>/dev/null | grep -o '"SYSTEM\$GET_SERVICE_STATUS[^"]*":"[^"]*"' | cut -d'"' -f4 || echo "")
    
    if echo "$STATUS" | grep -q "READY"; then
        echo "✅ Service is READY!"
        break
    fi
    echo "   Status: $STATUS (attempt $i/30)"
    sleep 2
done

# Get endpoint URL
echo ""
echo "🔗 Getting service endpoint..."
ENDPOINT=$(snow sql -q "SHOW ENDPOINTS IN SERVICE ${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME};" -c "$SNOWFLAKE_CONNECTION" -o json 2>/dev/null | grep -o '"ingress_url":"[^"]*"' | cut -d'"' -f4 | head -n 1 || echo "")

echo ""
echo "============================================"
echo "✨ Deployment Successful!"
echo "============================================"
if [ -n "$ENDPOINT" ]; then
    echo "🌐 Service URL: ${ENDPOINT}"
fi
echo ""
echo "📊 Useful commands:"
echo "   Status:  snow sql -q \"SELECT SYSTEM\\\$GET_SERVICE_STATUS('${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME}');\" -c $SNOWFLAKE_CONNECTION"
echo "   Logs:    snow sql -q \"SELECT SYSTEM\\\$GET_SERVICE_LOGS('${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME}', '0', 'e2e-flow-container', 100);\" -c $SNOWFLAKE_CONNECTION"
echo "   Suspend: snow sql -q \"ALTER SERVICE ${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME} SUSPEND;\" -c $SNOWFLAKE_CONNECTION"
echo "   Resume:  snow sql -q \"ALTER SERVICE ${DATABASE}.${APP_SCHEMA}.${SERVICE_NAME} RESUME;\" -c $SNOWFLAKE_CONNECTION"
echo "============================================"




