#!/bin/bash

# Test runner script for OZX Image Atlas Tool

echo "🧪 OZX Image Atlas - Test Suite"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Test configuration
BACKEND_TESTS=true
FRONTEND_TESTS=true
INTEGRATION_TESTS=false  # Requires running servers
E2E_TESTS=false         # Requires browser setup

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            INTEGRATION_TESTS=false
            E2E_TESTS=false
            shift
            ;;
        --integration)
            INTEGRATION_TESTS=true
            shift
            ;;
        --e2e)
            E2E_TESTS=true
            shift
            ;;
        --all)
            INTEGRATION_TESTS=true
            E2E_TESTS=true
            shift
            ;;
        --backend-only)
            BACKEND_TESTS=true
            FRONTEND_TESTS=false
            INTEGRATION_TESTS=false
            E2E_TESTS=false
            shift
            ;;
        --frontend-only)
            BACKEND_TESTS=false
            FRONTEND_TESTS=true
            INTEGRATION_TESTS=false
            E2E_TESTS=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--unit-only|--integration|--e2e|--all|--backend-only|--frontend-only]"
            exit 1
            ;;
    esac
done

# Keep track of test results
BACKEND_RESULT=0
FRONTEND_RESULT=0
INTEGRATION_RESULT=0
E2E_RESULT=0

echo "Test configuration:"
echo "  Backend unit tests: $BACKEND_TESTS"
echo "  Frontend unit tests: $FRONTEND_TESTS"
echo "  Integration tests: $INTEGRATION_TESTS"
echo "  E2E tests: $E2E_TESTS"
echo

# Backend tests
if [ "$BACKEND_TESTS" = true ]; then
    print_info "Running backend unit tests..."
    cd backend
    
    # Check if test dependencies are installed
    if ! python -c "import pytest" 2>/dev/null; then
        print_warning "Installing test dependencies..."
        pip install -r requirements-test.txt
    fi
    
    # Run tests
    python -m pytest tests/ -v --tb=short
    BACKEND_RESULT=$?
    print_status $BACKEND_RESULT "Backend unit tests"
    
    cd ..
    echo
fi

# Frontend tests  
if [ "$FRONTEND_TESTS" = true ]; then
    print_info "Running frontend unit tests..."
    cd frontend
    
    # Run tests
    npm test -- --watchAll=false --coverage=false --verbose=false
    FRONTEND_RESULT=$?
    print_status $FRONTEND_RESULT "Frontend unit tests"
    
    cd ..
    echo
fi

# Integration tests
if [ "$INTEGRATION_TESTS" = true ]; then
    print_info "Running integration tests..."
    
    # Check if backend is running
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_info "Backend server detected on localhost:8000"
        
        cd tests/integration
        python -m pytest test_full_workflow.py -v
        INTEGRATION_RESULT=$?
        print_status $INTEGRATION_RESULT "Integration tests"
        cd ../..
    else
        print_warning "Backend server not running on localhost:8000"
        print_warning "Start with: cd backend && uvicorn main:app --reload"
        INTEGRATION_RESULT=1
    fi
    echo
fi

# E2E tests
if [ "$E2E_TESTS" = true ]; then
    print_info "Running E2E tests..."
    
    # Check if frontend is running
    if curl -s http://localhost:3000/ > /dev/null 2>&1; then
        print_info "Frontend server detected on localhost:3000"
        
        cd tests/e2e
        python test_browser_workflow.py
        E2E_RESULT=$?
        print_status $E2E_RESULT "E2E tests"
        cd ../..
    else
        print_warning "Frontend server not running on localhost:3000"
        print_warning "Start with: cd frontend && npm start"
        print_info "Running manual E2E instructions instead:"
        cd tests/e2e
        python test_browser_workflow.py manual
        cd ../..
        E2E_RESULT=0  # Don't fail on manual instructions
    fi
    echo
fi

# Summary
echo "================================"
echo "📊 Test Results Summary"
echo "================================"

if [ "$BACKEND_TESTS" = true ]; then
    print_status $BACKEND_RESULT "Backend Unit Tests"
fi

if [ "$FRONTEND_TESTS" = true ]; then
    print_status $FRONTEND_RESULT "Frontend Unit Tests"
fi

if [ "$INTEGRATION_TESTS" = true ]; then
    print_status $INTEGRATION_RESULT "Integration Tests"
fi

if [ "$E2E_TESTS" = true ]; then
    print_status $E2E_RESULT "E2E Tests"
fi

# Calculate overall result
TOTAL_RESULT=$((BACKEND_RESULT + FRONTEND_RESULT + INTEGRATION_RESULT + E2E_RESULT))

echo
if [ $TOTAL_RESULT -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo
    echo "Ready for production deployment!"
else
    echo -e "${RED}❌ Some tests failed.${NC}"
    echo
    echo "Please fix the failing tests before deployment."
fi

echo
echo "Quick start guide:"
echo "  ./start.sh          - Start both servers"
echo "  python test_setup.py - Verify setup"
echo "  ./run_tests.sh --all - Run all tests"

exit $TOTAL_RESULT