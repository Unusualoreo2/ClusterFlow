#!/bin/bash
# HPCFlow - Test MVP

# Set variables
APP_DIR="$(dirname "$0")"
DATA_DIR="$APP_DIR/../data"

# Check if data file exists
if [ ! -f "$DATA_DIR/example.sacct.csv" ]; then
    echo "❌ Example file not found: $DATA_DIR/example.sacct.csv"
    exit 1
fi

# Run test
echo "🧪 Testing HPCFlow with example data..."

# Simulate upload via curl
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: text/csv" \
  -F "file=@$DATA_DIR/example.sacct.csv" \
  -v

# Check if successful
if [ $? -eq 0 ]; then
    echo "✅ Test passed: response received"
else
    echo "❌ Test failed: no response"
fi