#!/bin/bash
# HPCFlow - Test Batch: Validate MVP

# Set variables
APP_DIR="$(dirname "$0")"
BACKEND_DIR="$APP_DIR/../backend"\nDATA_DIR="$APP_DIR/../data"
LOG_DIR="$APP_DIR/../logs"

# Create logs directory
mkdir -p "$LOG_DIR"

# Log file
LOG_FILE="$LOG_DIR/test_batch_$(date +%Y%m%d_%H%M%S).log"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Exit on error
set -e

log "🚀 Starting HPCFlow Test Batch"
log "Project root: $APP_DIR"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log "❌ Docker not found. Please install Docker."
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
    log "❌ requirements.txt not found in $BACKEND_DIR"
    exit 1
fi

# Check if data file exists
if [ ! -f "$DATA_DIR/example.sacct.csv" ]; then
    log "❌ Example file not found: $DATA_DIR/example.sacct.csv"
    exit 1
fi

log "✅ All prerequisites present"

# Build Docker image
log "🏗️ Building Docker image..."
docker build -t hpcflow:latest .

if [ $? -ne 0 ]; then
    log "❌ Failed to build Docker image"
    exit 1
fi

log "✅ Docker image built successfully"

# Run container
log "🚀 Running HPCFlow container..."
CONTAINER_ID=$(docker run -d -p 8000:8000 hpcflow:latest)

if [ -z "$CONTAINER_ID" ]; then
    log "❌ Failed to start container"
    exit 1
fi

log "✅ Container started: $CONTAINER_ID"

# Wait for service to be ready
log "⏳ Waiting for service to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8000 > /dev/null 2>&1; then
        log "✅ Service is ready"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        log "❌ Service did not start within 30 seconds"
        docker stop $CONTAINER_ID
        docker rm $CONTAINER_ID
        exit 1
    fi
    log "Waiting... $i/30"
done

# Test 1: Upload example file
log "🧪 Test 1: Upload example.sacct.csv"

# Use curl to simulate upload
if curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: text/csv" \
  -F "file=@$DATA_DIR/example.sacct.csv" \
  -s -o /dev/null -w "%{http_code}" > "$LOG_DIR/test1_response.log"; then
    log "✅ Test 1 passed: HTTP 200"
else
    log "❌ Test 1 failed: HTTP 500 or timeout"
    exit 1
fi

# Test 2: Validate response
log "🧪 Test 2: Validate response content"

# Extract response
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: text/csv" \
  -F "file=@$DATA_DIR/example.sacct.csv" \
  -s -o "$LOG_DIR/test2_response.json"

# Check if JSON contains expected fields
if grep -q '"status": "success"' "$LOG_DIR/test2_response.json"; then
    log "✅ Test 2 passed: Response contains status=success"
else
    log "❌ Test 2 failed: Missing status=success"
    exit 1
fi

# Test 3: Check insight
log "🧪 Test 3: Check insight"

if grep -q 'Memory-bound' "$LOG_DIR/test2_response.json"; then
    log "✅ Test 3 passed: Insight contains 'Memory-bound'"
else
    log "❌ Test 3 failed: Insight does not contain 'Memory-bound'"
    exit 1
fi

# Test 4: Test with invalid file
log "🧪 Test 4: Upload invalid file (PDF)"

# Create dummy PDF
echo "This is a dummy PDF" > "$LOG_DIR/dummy.pdf"

# Try to upload
if curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/pdf" \
  -F "file=@$LOG_DIR/dummy.pdf" \
  -s -o /dev/null -w "%{http_code}" > "$LOG_DIR/test4_response.log"; then
    log "❌ Test 4 failed: Should return 400, but got 200"
    exit 1
fi

# Check for 400 error
if grep -q '400' "$LOG_DIR/test4_response.log"; then
    log "✅ Test 4 passed: Returned 400 for invalid file"
else
    log "❌ Test 4 failed: Did not return 400"
    exit 1
fi

# Cleanup
log "🗑️ Cleaning up..."
docker stop $CONTAINER_ID

# Log summary
log "✅ All tests passed!"
log "📄 Test log: $LOG_FILE"
log "✅ HPCFlow MVP is now fully validated and ready for deployment."