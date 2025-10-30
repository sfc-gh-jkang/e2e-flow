#!/bin/bash

# Entrypoint script for Prefect worker on Snowflake SPCS
set -e

echo "🚀 Starting Prefect worker on Snowflake SPCS..."

# Check for required environment variables
if [ -z "$PREFECT_API_URL" ]; then
    echo "❌ ERROR: PREFECT_API_URL environment variable is not set!"
    exit 1
fi

if [ -z "$PREFECT_API_KEY" ]; then
    echo "❌ ERROR: PREFECT_API_KEY environment variable is not set!"
    exit 1
fi

# Optional: Run prefect cloud login if needed
# This is generally NOT necessary as Prefect SDK uses env vars automatically
if [ "$PREFECT_CLOUD_LOGIN" = "true" ]; then
    echo "🔐 Logging into Prefect Cloud..."
    prefect cloud login -k "$PREFECT_API_KEY" --workspace-handle "$PREFECT_WORKSPACE_HANDLE" || {
        echo "⚠️  Warning: Prefect cloud login failed, but continuing anyway..."
        echo "   The SDK will authenticate using environment variables"
    }
fi

echo "✅ Connected to Prefect Cloud: $PREFECT_API_URL"
echo "✅ Starting worker..."

# Execute the main command
exec "$@"




