#!/bin/bash

# Create necessary directories
mkdir -p uploads instance

# Check if Redis is running
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Redis is not running. Please start Redis first."
    exit 1
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A celery_worker.celery worker --loglevel=info -P threads &
CELERY_PID=$!
echo "Celery worker started with PID: $CELERY_PID"

# Start Flask app
echo "Starting Flask app..."
python app.py

# When Flask app is terminated, also terminate Celery worker
echo "Shutting down Celery worker..."
kill $CELERY_PID 