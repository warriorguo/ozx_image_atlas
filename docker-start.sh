#!/bin/bash

# Docker startup script for OZX Image Atlas Tool

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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
echo -e "${BLUE}🐳 OZX Image Atlas Tool - Docker Deployment${NC}"
echo "=============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Parse command line arguments
ENVIRONMENT="development"
PROFILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --prod|--production)
            ENVIRONMENT="production"
            PROFILE="--profile production"
            shift
            ;;
        --dev|--development)
            ENVIRONMENT="development"
            shift
            ;;
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --down)
            print_status "Stopping and removing containers..."
            docker-compose down -v
            print_success "Containers stopped and removed."
            exit 0
            ;;
        --logs)
            print_status "Showing container logs..."
            docker-compose logs -f
            exit 0
            ;;
        --status)
            print_status "Container status:"
            docker-compose ps
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --prod, --production  Run in production mode with nginx proxy"
            echo "  --dev, --development  Run in development mode (default)"
            echo "  --build              Force rebuild of images"
            echo "  --down               Stop and remove containers"
            echo "  --logs               Show container logs"
            echo "  --status             Show container status"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_status "Starting OZX Image Atlas Tool in $ENVIRONMENT mode..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Set environment variables
export COMPOSE_PROJECT_NAME=ozx-atlas

if [ "$ENVIRONMENT" = "production" ]; then
    print_status "Production mode: Starting with nginx reverse proxy..."
    print_warning "Make sure to configure proper domain and SSL in production!"
fi

# Build and start containers
print_status "Building and starting containers..."
if [ -n "$BUILD_FLAG" ]; then
    print_status "Forcing rebuild of images..."
fi

# Use docker-compose or docker compose based on availability
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Start services
$DOCKER_COMPOSE up -d $BUILD_FLAG $PROFILE

# Wait for services to be healthy
print_status "Waiting for services to start..."
sleep 10

# Check service health
print_status "Checking service health..."

# Check backend
if curl -s http://localhost:8000/ > /dev/null; then
    print_success "✅ Backend is running on http://localhost:8000"
else
    print_error "❌ Backend is not responding"
fi

# Check frontend
if curl -s http://localhost:3000/ > /dev/null; then
    print_success "✅ Frontend is running on http://localhost:3000"
else
    print_error "❌ Frontend is not responding"
fi

# Production specific checks
if [ "$ENVIRONMENT" = "production" ]; then
    if curl -s http://localhost:80/ > /dev/null; then
        print_success "✅ Nginx proxy is running on http://localhost:80"
    else
        print_error "❌ Nginx proxy is not responding"
    fi
fi

echo ""
echo "=============================================="
print_success "🎉 OZX Image Atlas Tool is now running!"
echo ""

if [ "$ENVIRONMENT" = "production" ]; then
    echo "📱 Application URLs:"
    echo "   Main: http://localhost"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend API: http://localhost:8000"
else
    echo "📱 Application URLs:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend API: http://localhost:8000"
fi

echo ""
echo "🔧 Management commands:"
echo "   View logs:    $0 --logs"
echo "   Check status: $0 --status" 
echo "   Stop all:     $0 --down"
echo ""

# Show container status
print_status "Container status:"
$DOCKER_COMPOSE ps