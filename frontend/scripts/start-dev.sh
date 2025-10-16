#!/bin/sh

# FlyEsports Frontend Development Startup Script
set -e

echo "Starting FlyEsports Frontend Development Server..."
echo "Node Environment: ${NODE_ENV:-development}"
echo "API Base URL: ${VITE_API_BASE_URL:-http://localhost:8000/api/v1}"

# Function to handle shutdown gracefully
cleanup() {
    echo "Shutting down development server..."
    if [ ! -z "$VITE_PID" ]; then
        kill -TERM "$VITE_PID" 2>/dev/null || true
        wait "$VITE_PID" 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Create necessary directories
mkdir -p /app/logs

# Check if backend is available (with retries)
echo "Checking backend availability..."
BACKEND_URL="${VITE_API_BASE_URL:-http://localhost:8000/api/v1}"
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "${BACKEND_URL%/api/v1}/health" > /dev/null 2>&1; then
        echo "Backend is available"
        break
    else
        echo "Backend not ready, waiting... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Warning: Backend is not available after $MAX_RETRIES attempts, starting anyway..."
fi

# Clear Vite cache if needed
if [ "${CLEAR_CACHE:-false}" = "true" ]; then
    echo "Clearing Vite cache..."
    rm -rf /app/.vite
    mkdir -p /app/.vite
fi

# Start Vite development server
echo "Starting Vite development server on port 3000..."
exec npm run dev -- \
    --host 0.0.0.0 \
    --port 3000 \
    --clearScreen false \
    --logLevel info &

VITE_PID=$!
echo "Vite server started with PID: $VITE_PID"

# Wait for the main process
wait $VITE_PID