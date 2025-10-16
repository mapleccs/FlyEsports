#!/bin/bash

# FlyEsports Backend Startup Script
set -e

echo "Starting FlyEsports Backend..."
echo "Environment: ${ENVIRONMENT:-development}"
echo "Debug Mode: ${DEBUG:-false}"

# Function to handle shutdown gracefully
cleanup() {
    echo "Shutting down gracefully..."
    if [ ! -z "$MAIN_PID" ]; then
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        wait "$MAIN_PID" 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Create necessary directories
mkdir -p /app/logs

# Wait for database connection (with timeout)
echo "Checking database connection..."
python -c "
import asyncio
import asyncpg
import os
import sys
from urllib.parse import urlparse

async def check_db():
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url:
        print('No DATABASE_URL provided')
        return False
    
    parsed = urlparse(db_url)
    try:
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else 'postgres'
        )
        await conn.close()
        print('Database connection successful')
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

if not asyncio.run(check_db()):
    sys.exit(1)
"

# Check Redis connection
echo "Checking Redis connection..."
python -c "
import redis
import os
import sys
from urllib.parse import urlparse

redis_url = os.getenv('REDIS_URL', '')
if not redis_url:
    print('No REDIS_URL provided')
    sys.exit(1)

try:
    r = redis.from_url(redis_url)
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
    sys.exit(1)
"

# Run database migrations (only for main backend service)
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

# Start the application based on service type
case "${SERVICE_TYPE:-api}" in
    "api")
        echo "Starting FastAPI server..."
        if [ "${ENVIRONMENT:-production}" = "development" ]; then
            echo "Development mode: enabling hot reload..."
            exec uvicorn src.presentation.api.main:app \
                --host 0.0.0.0 \
                --port 8000 \
                --access-log \
                --log-level info \
                --reload \
                --reload-dir src &
        else
            exec uvicorn src.presentation.api.main:app \
                --host 0.0.0.0 \
                --port 8000 \
                --access-log \
                --log-level info &
        fi
        ;;
    "worker")
        echo "Starting Celery worker..."
        exec celery -A src.infrastructure.tasks.celery_app worker \
            --loglevel=info \
            --concurrency=${WORKER_CONCURRENCY:-2} \
            -Q high_priority,medium_priority,low_priority \
            --max-tasks-per-child=1000 \
            --prefetch-multiplier=1 &
        ;;
    "beat")
        echo "Starting Celery beat scheduler..."
        exec celery -A src.infrastructure.tasks.celery_app beat \
            --loglevel=info \
            --schedule=/app/celerybeat-schedule \
            --pidfile=/app/celerybeat.pid &
        ;;
    "flower")
        echo "Starting Celery flower monitoring..."
        exec celery -A src.infrastructure.tasks.celery_app flower \
            --port=5555 \
            --broker=${CELERY_BROKER_URL} \
            --persistent=True \
            --db=/app/flower_db &
        ;;
    *)
        echo "Unknown service type: ${SERVICE_TYPE}"
        exit 1
        ;;
esac

MAIN_PID=$!
echo "Service started with PID: $MAIN_PID"

# Wait for the main process
wait $MAIN_PID