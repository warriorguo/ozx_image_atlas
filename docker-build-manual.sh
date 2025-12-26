#!/bin/bash

# Manual Docker build and run script (without docker-compose)
# For systems where docker-compose is not available

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print header
echo -e "${BLUE}🐳 OZX Image Atlas Tool - Manual Docker Build${NC}"
echo "================================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Parse command line arguments
ACTION="start"
BUILD_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --logs)
            ACTION="logs"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --build     Force rebuild of images"
            echo "  --stop      Stop and remove containers"
            echo "  --status    Show container status"
            echo "  --logs      Show container logs"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Network name
NETWORK_NAME="ozx-atlas-network"

case $ACTION in
    "stop")
        print_status "Stopping containers..."
        docker stop ozx-atlas-backend ozx-atlas-frontend 2>/dev/null || true
        docker rm ozx-atlas-backend ozx-atlas-frontend 2>/dev/null || true
        docker network rm $NETWORK_NAME 2>/dev/null || true
        print_success "Containers stopped and removed."
        exit 0
        ;;
    "status")
        print_status "Container status:"
        docker ps --filter name=ozx-atlas --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        exit 0
        ;;
    "logs")
        print_status "Container logs:"
        echo "=== Backend logs ==="
        docker logs ozx-atlas-backend --tail 50 2>/dev/null || echo "Backend not running"
        echo ""
        echo "=== Frontend logs ==="
        docker logs ozx-atlas-frontend --tail 50 2>/dev/null || echo "Frontend not running"
        exit 0
        ;;
esac

# Create network
print_status "Creating Docker network..."
docker network create $NETWORK_NAME 2>/dev/null || print_warning "Network already exists"

# Build backend image
print_status "Building backend image..."
docker build -t ozx-atlas-backend ./backend

# Build frontend image
print_status "Building frontend image..."
docker build -t ozx-atlas-frontend ./frontend

# Stop existing containers
print_status "Stopping existing containers..."
docker stop ozx-atlas-backend ozx-atlas-frontend 2>/dev/null || true
docker rm ozx-atlas-backend ozx-atlas-frontend 2>/dev/null || true

# Start backend container
print_status "Starting backend container..."
docker run -d \
    --name ozx-atlas-backend \
    --network $NETWORK_NAME \
    -p 8000:8000 \
    -e ENV=production \
    -e PYTHONPATH=/app \
    --restart unless-stopped \
    ozx-atlas-backend

# Wait for backend to start
print_status "Waiting for backend to start..."
sleep 5

# Start frontend container
print_status "Starting frontend container..."
docker run -d \
    --name ozx-atlas-frontend \
    --network $NETWORK_NAME \
    -p 3000:80 \
    -e REACT_APP_API_URL=http://localhost:8000 \
    --restart unless-stopped \
    ozx-atlas-frontend

# Wait for services to start
print_status "Waiting for services to start..."
sleep 10

# Health checks
print_status "Checking service health..."

if curl -s http://localhost:8000/ > /dev/null; then
    print_success "✅ Backend is running on http://localhost:8000"
else
    print_error "❌ Backend is not responding"
    print_status "Backend logs:"
    docker logs ozx-atlas-backend --tail 20
fi

if curl -s http://localhost:3000/ > /dev/null; then
    print_success "✅ Frontend is running on http://localhost:3000"
else
    print_error "❌ Frontend is not responding"
    print_status "Frontend logs:"
    docker logs ozx-atlas-frontend --tail 20
fi

echo ""
echo "================================================"
print_success "🎉 OZX Image Atlas Tool is now running!"
echo ""
echo "📱 Application URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo ""
echo "🔧 Management commands:"
echo "   Stop all:     $0 --stop"
echo "   View logs:    $0 --logs"
echo "   Check status: $0 --status"
echo ""

# Show container status
print_status "Container status:"
docker ps --filter name=ozx-atlas --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"