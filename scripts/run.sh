#!/bin/bash
# HPCFlow - Run MVP (Optimized)

# Set variables
APP_DIR="$(dirname "$0")"
BACKEND_DIR="$APP_DIR/../backend"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
    echo "❌ requirements.txt not found in $BACKEND_DIR"
    exit 1
fi

# Build and run
echo "🚀 Building HPCFlow Docker image..."
docker build -t hpcflow:optimized .

if [ $? -ne 0 ]; then
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo "✅ Docker image built successfully"

echo "🚀 Running HPCFlow..."
docker run -p 8000:8000 --rm hpcflow:optimized

if [ $? -ne 0 ]; then
    echo "❌ Failed to run container"
    exit 1
fi

echo "🌐 Access HPCFlow at http://localhost:8000"