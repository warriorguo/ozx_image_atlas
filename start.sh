#!/bin/bash

# OZX Image Atlas Tool - Development Startup Script

echo "Starting OZX Image Atlas Tool..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
if ! command_exists python3; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

if ! command_exists npm; then
    echo "Error: Node.js and npm are required but not installed."
    exit 1
fi

# Start backend
echo "Starting backend server..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "Backend starting on http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend server..."
cd ../frontend
npm install
echo "Frontend starting on http://localhost:3000"
npm start &
FRONTEND_PID=$!

# Cleanup function
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on exit
trap cleanup SIGINT SIGTERM

echo ""
echo "✅ OZX Image Atlas Tool is running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait