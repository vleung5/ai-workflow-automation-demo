#!/bin/sh
set -e

echo "Starting AI Workflow Automation Demo..."
echo "Environment: ${ENV:-dev}"
echo "Version: ${DD_VERSION:-2.0.0}"

# Wait for dependencies (Redis for Celery, if needed)
if [ -n "${CELERY_BROKER_URL}" ]; then
    echo "Waiting for Redis..."
    until python -c "import redis; redis.Redis.from_url('${CELERY_BROKER_URL}').ping()" 2>/dev/null; do
        echo "Redis not ready, retrying in 2s..."
        sleep 2
    done
    echo "Redis is ready"
fi

# Apply database migrations
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    python scripts/migrate_db.py
fi

# Start the application
exec "$@"
