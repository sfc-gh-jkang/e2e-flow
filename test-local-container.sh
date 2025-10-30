#!/bin/bash

# Local Container Testing Script
# Based on: https://github.com/sfc-gh-jkang/cortex-cost-app-spcs

set -e

CONTAINER_NAME="e2e-flow-local"
IMAGE_NAME="e2e-flow"
IMAGE_TAG="latest"
PORT=8080

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --build    Build the Docker image before running"
    echo "  --logs     Show container logs"
    echo "  --shell    Open a shell in the running container"
    echo "  --stop     Stop and remove the container"
    echo "  --test     Run tests in the container"
    echo "  --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --build  # Build and run container"
    echo "  $0          # Run container with existing image"
    echo "  $0 --logs   # View container logs"
    echo "  $0 --shell  # Open shell in container"
    exit 0
}

build_image() {
    echo "🐳 Building Docker image..."
    docker build --platform linux/amd64 -t ${IMAGE_NAME}:${IMAGE_TAG} .
    echo "✅ Build complete!"
}

run_container() {
    # Stop and remove existing container if it exists
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        echo "⚠️  Warning: .env file not found!"
        echo ""
        echo "Create one with:"
        echo "  ./setup-prefect-env.sh"
        echo ""
        echo "Or manually create .env with:"
        echo "  PREFECT_API_URL=your-prefect-api-url"
        echo "  PREFECT_API_KEY=your-prefect-api-key"
        echo "  PREFECT_WORK_POOL=spcs-process"
        echo ""
        read -p "Continue without .env file? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ENV_FILE_ARG=""
    else
        echo "✅ Found .env file"
        ENV_FILE_ARG="--env-file .env"
    fi
    
    echo "🚀 Starting container..."
    docker run -d \
        --name ${CONTAINER_NAME} \
        --platform linux/amd64 \
        -p ${PORT}:8080 \
        ${ENV_FILE_ARG} \
        ${IMAGE_NAME}:${IMAGE_TAG}
    
    echo "✅ Container started!"
    echo "🌐 Access at: http://localhost:${PORT}"
    echo ""
    echo "Useful commands:"
    echo "  Logs:  docker logs -f ${CONTAINER_NAME}"
    echo "  Shell: docker exec -it ${CONTAINER_NAME} /bin/bash"
    echo "  Stop:  docker stop ${CONTAINER_NAME}"
}

show_logs() {
    echo "📋 Container logs:"
    docker logs -f ${CONTAINER_NAME}
}

open_shell() {
    echo "🐚 Opening shell in container..."
    docker exec -it ${CONTAINER_NAME} /bin/bash
}

stop_container() {
    echo "🛑 Stopping container..."
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    echo "✅ Container stopped and removed"
}

run_tests() {
    echo "🧪 Running tests in container..."
    docker exec ${CONTAINER_NAME} python -c "import sys; print(f'Python version: {sys.version}')"
    echo "✅ Basic tests passed"
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    run_container
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            build_image
            run_container
            exit 0
            ;;
        --logs)
            show_logs
            exit 0
            ;;
        --shell)
            open_shell
            exit 0
            ;;
        --stop)
            stop_container
            exit 0
            ;;
        --test)
            run_tests
            exit 0
            ;;
        --help)
            print_usage
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            ;;
    esac
    shift
done

