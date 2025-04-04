#!/bin/bash

# ===== Configuration =====
DEBUG_MODE=true
LOG_FILE="debug.log"
REDIS_REQUIRED=true

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# ===== Functions =====

# Function to display banner
show_banner() {
    echo "=============================================="
    echo "     Transcription Application - Debug Mode   "
    echo "=============================================="
    echo ""
}

# Function to start the Celery worker
start_celery() {
    echo "Starting Celery worker..."
    # Show Redis connection info (safely)
    if [ -n "$CELERY_BROKER_URL" ]; then
        SAFE_URL=$(echo $CELERY_BROKER_URL | sed 's/\(rediss\?:\/\/[^:]*:\)[^@]*\(@.*\)/\1*****\2/')
        echo "Using Redis at: $SAFE_URL"
    fi
    
    celery -A celery_worker.celery worker --loglevel=info -P threads &
    CELERY_PID=$!
    echo "Celery worker started with PID: $CELERY_PID"
}

# Function to start the Flask application
start_flask() {
    echo "Starting Flask app..."
    FLASK_ENV=production FLASK_DEBUG=1 python app.py
}

# ===== Main Execution =====

# Display banner
show_banner

# Create necessary directories
mkdir -p uploads instance

# Start Celery worker
start_celery

# Start Flask app
start_flask

# When Flask app is terminated, also terminate Celery worker
echo "Shutting down Celery worker..."
kill $CELERY_PID 2>/dev/null

echo "Application terminated."