#!/bin/bash

# ===== Configuration =====
DEBUG_MODE=true
LOG_FILE="debug.log"
REDIS_REQUIRED=true

# ===== Functions =====

# Function to display banner
show_banner() {
    echo "=============================================="
    echo "     Transcription Application - Debug Mode   "
    echo "=============================================="
    echo ""
}

# Function to check if Redis is running
check_redis() {
    echo "Checking Redis connection..."
    redis-cli ping > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Redis is not running!"
        if [ "$REDIS_REQUIRED" == true ]; then
            echo "Redis is required. Please start Redis first with: redis-server"
            echo "Then run this script again."
            exit 1
        else
            echo "Warning: Continuing without Redis, but the application will likely fail."
        fi
    else
        echo "Redis is running."
    fi
}

# Function to start the Celery worker
start_celery() {
    echo "Starting Celery worker..."
    celery -A celery_worker.celery worker --loglevel=info -P threads &
    CELERY_PID=$!
    echo "Celery worker started with PID: $CELERY_PID"
}

# Function to start the Flask application
start_flask() {
    echo "Starting Flask app..."
    FLASK_ENV=development FLASK_DEBUG=1 python app.py
}

# ===== Main Execution =====

# Display banner
show_banner

# Create necessary directories
mkdir -p uploads instance

# Check Redis status
check_redis

# Start Celery worker
start_celery

# Start Flask app
start_flask

# When Flask app is terminated, also terminate Celery worker
echo "Shutting down Celery worker..."
kill $CELERY_PID 2>/dev/null

echo "Application terminated."