#!/bin/bash

# GitHub Container Registry Build and Push Script
# Builds and pushes Docker image to ghcr.io

set -e

# Configuration - Update these values as needed
GITHUB_USERNAME="sfc-gh-jkang"
IMAGE_NAME="e2e-flow"
IMAGE_TAG="latest"
GHCR_REGISTRY="ghcr.io"

# Parse command line arguments
LOCAL_ONLY=false
NO_CACHE=false

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --local           Build only (don't push)"
    echo "  --no-cache        Build without using cache"
    echo "  --tag TAG         Use custom tag (default: latest)"
    echo "  --username USER   GitHub username (default: sfc-gh-jkang)"
    echo "  --help            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  CR_PAT            GitHub Personal Access Token (required for push)"
    echo ""
    echo "Examples:"
    echo "  $0                           # Build and push with tag 'latest'"
    echo "  $0 --local                   # Build only, don't push"
    echo "  $0 --tag v1.0.0              # Build and push with custom tag"
    echo "  $0 --no-cache                # Build without cache"
    echo ""
    echo "Setup:"
    echo "  1. Create a GitHub Personal Access Token with 'write:packages' scope"
    echo "  2. Export it: export CR_PAT=your_token_here"
    echo "  3. Login: echo \$CR_PAT | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin"
    echo ""
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            LOCAL_ONLY=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --username)
            GITHUB_USERNAME="$2"
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

# Construct full image path
FULL_IMAGE_PATH="${GHCR_REGISTRY}/${GITHUB_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "============================================"
echo "🐳 GitHub Container Registry Build & Push"
echo "============================================"
echo "📦 Image: ${FULL_IMAGE_PATH}"
echo "🏷️  Tag: ${IMAGE_TAG}"
if [ "$LOCAL_ONLY" = true ]; then
    echo "🔧 Mode: Local build only"
else
    echo "🔧 Mode: Build and push"
fi
echo "============================================"
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Build Docker image
echo "🏗️  Building Docker image for linux/amd64..."
if [ "$NO_CACHE" = true ]; then
    docker build --platform linux/amd64 --no-cache -t ${FULL_IMAGE_PATH} .
else
    docker build --platform linux/amd64 -t ${FULL_IMAGE_PATH} .
fi

echo "✅ Build complete!"

# If local only, exit here
if [ "$LOCAL_ONLY" = true ]; then
    echo ""
    echo "============================================"
    echo "✨ Local Build Complete!"
    echo "============================================"
    echo "🐳 Image: ${FULL_IMAGE_PATH}"
    echo ""
    echo "📊 Test locally with:"
    echo "   docker run -p 8080:8080 ${FULL_IMAGE_PATH}"
    echo "============================================"
    exit 0
fi

# Check if logged in to GitHub Container Registry
echo ""
echo "🔐 Checking GitHub Container Registry authentication..."

# Check if CR_PAT is set
if [ -z "$CR_PAT" ]; then
    echo "⚠️  Warning: CR_PAT environment variable not set"
    echo ""
    echo "To push to GitHub Container Registry, you need to:"
    echo "  1. Create a Personal Access Token at: https://github.com/settings/tokens"
    echo "     (Grant 'write:packages' and 'read:packages' scopes)"
    echo "  2. Export it: export CR_PAT=your_token_here"
    echo "  3. Login: echo \$CR_PAT | docker login ghcr.io -u ${GITHUB_USERNAME} --password-stdin"
    echo ""
    echo "Would you like to continue with push anyway? (You may already be logged in)"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Push cancelled."
        exit 0
    fi
fi

# Test docker login
if ! docker login ${GHCR_REGISTRY} --username ${GITHUB_USERNAME} --password-stdin <<< "$CR_PAT" 2>/dev/null; then
    echo "⚠️  Could not verify GitHub Container Registry login"
    echo "Attempting push anyway (you may already be logged in)..."
fi

# Push image
echo ""
echo "⬆️  Pushing image to GitHub Container Registry..."
docker push ${FULL_IMAGE_PATH}

echo ""
echo "============================================"
echo "✨ Build and Push Complete!"
echo "============================================"
echo "🐳 Image: ${FULL_IMAGE_PATH}"
echo ""
echo "📊 Your image is now available at:"
echo "   https://github.com/${GITHUB_USERNAME}/${IMAGE_NAME}/pkgs/container/${IMAGE_NAME}"
echo ""
echo "🚀 Pull with:"
echo "   docker pull ${FULL_IMAGE_PATH}"
echo ""
echo "📦 To make the image public (if needed):"
echo "   Go to: https://github.com/users/${GITHUB_USERNAME}/packages/container/${IMAGE_NAME}/settings"
echo "============================================"
