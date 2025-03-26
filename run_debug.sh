#!/bin/bash

# ===== Configuration =====
DEBUG_MODE=true  # Set to true to enable extensive debugging
LOG_FILE_UPLOAD="upload_debug.log"
LOG_FILE_TASKS="transcription_tasks.log"
REDIS_REQUIRED=true

# ===== Functions =====

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --no-debug         Run without debug logging"
    echo "  --skip-redis-check Skip Redis availability check"
    echo "  --help             Show this help message"
}

# Function to display banner
show_banner() {
    echo "=============================================="
    echo "     NSWCC Transcription Demo Application    "
    echo "=============================================="
    echo "Combined run and debug script                "
    echo "Debug mode: $([ "$DEBUG_MODE" == true ] && echo "ON" || echo "OFF")"
    echo "=============================================="
    echo ""
}

# Parse command line arguments
parse_args() {
    for arg in "$@"; do
        case $arg in
            --no-debug)
                DEBUG_MODE=false
                shift
                ;;
            --skip-redis-check)
                REDIS_REQUIRED=false
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                # Unknown option
                echo "Unknown option: $arg"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Function to clear log files
clear_logs() {
    if [ "$DEBUG_MODE" == true ]; then
        echo "Clearing existing log files..."
        > "$LOG_FILE_UPLOAD"
        > "$LOG_FILE_TASKS"
        echo "Logs cleared."
    fi
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

# Function to check Celery worker status
check_celery() {
    echo "=== Checking Celery worker status ==="
    ps aux | grep -i celery | grep -v grep
    
    if [ "$DEBUG_MODE" == true ]; then
        echo ""
        echo "=== Checking Redis details ==="
        redis-cli info | grep connected
        redis-cli info | grep used_memory
        
        echo ""
        echo "=== Checking Redis queue status ==="
        redis-cli llen celery
        redis-cli type celery
    fi
}

# Function to check for stuck tasks
check_stuck_tasks() {
    if [ "$DEBUG_MODE" == true ]; then
        echo "=== Checking database for stuck tasks ==="
        
        echo "Files with status 'processing':"
        sqlite3 instance/app.db "SELECT id, filename, status, current_stage, progress_percent, upload_time FROM file WHERE status = 'processing';"
        
        echo ""
        echo "Files with errors:"
        sqlite3 instance/app.db "SELECT id, filename, status, error_message, upload_time FROM file WHERE status = 'error';"
    fi
}

# Function to diagnose common issues
diagnose_common_issues() {
    if [ "$DEBUG_MODE" == true ]; then
        echo "=== Diagnosing common issues ==="
        
        echo "Checking disk space:"
        df -h
        
        echo ""
        echo "Checking memory usage:"
        free -h
        
        if [ -f "$LOG_FILE_UPLOAD" ] && [ -f "$LOG_FILE_TASKS" ]; then
            echo ""
            echo "Checking for Azure connection issues:"
            grep -i "azure\|blob\|storage" "$LOG_FILE_UPLOAD" "$LOG_FILE_TASKS" 2>/dev/null | grep -i "error\|fail\|exception" || echo "No Azure issues found in logs."
            
            echo ""
            echo "Checking for file size issues:"
            grep -i "size\|bytes\|mb\|gb" "$LOG_FILE_UPLOAD" "$LOG_FILE_TASKS" 2>/dev/null | grep -i "warn\|error\|large" || echo "No file size issues found in logs."
            
            echo ""
            echo "Checking for timeouts or slow operations:"
            grep -i "timeout\|seconds\|complete" "$LOG_FILE_UPLOAD" "$LOG_FILE_TASKS" 2>/dev/null | grep -i "warn\|error\|slow\|exceed" || echo "No timeout issues found in logs."
        fi
    fi
}

# Function to show application-specific troubleshooting recommendations
show_recommendations() {
    if [ "$DEBUG_MODE" == true ]; then
        echo "=== Troubleshooting Recommendations ==="
        echo ""
        echo "1. If uploads are getting stuck at 'Processing file, please wait...':"
        echo "   - Check the debug logs for errors:"
        echo "     tail -f $LOG_FILE_UPLOAD $LOG_FILE_TASKS"
        echo "   - Verify Azure credentials and connectivity"
        echo "   - Check if Celery worker is processing tasks"
        echo ""
        echo "2. To reset a stuck file, run:"
        echo "   sqlite3 instance/app.db \"UPDATE file SET status = 'uploaded', current_stage = NULL, progress_percent = 0 WHERE id = '<file_id>';\""
        echo ""
        echo "3. Common issues:"
        echo "   - Redis connection problems: ensure Redis is running"
        echo "   - File size too large: check available disk space"
        echo "   - Azure connectivity: verify network connectivity and credentials"
        echo "   - Python dependencies: ensure all dependencies are installed"
        echo ""
    fi
}

# Function to start log monitoring in a separate terminal window
start_log_monitoring() {
    if [ "$DEBUG_MODE" == true ]; then
        echo "Opening log monitoring in a new terminal window..."
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "echo 'Monitoring logs for NSWCC Transcription Demo'; echo '(Press Ctrl+C to stop monitoring)'; echo ''; tail -f $LOG_FILE_UPLOAD $LOG_FILE_TASKS | grep --color=auto -E 'error|ERROR|fail|FAIL|exception|Exception|Processing file, please wait|Starting transcription'; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "tail -f $LOG_FILE_UPLOAD $LOG_FILE_TASKS | grep --color=auto -E 'error|ERROR|fail|FAIL|exception|Exception|Processing file, please wait|Starting transcription'"
        else
            echo "Cannot open a new terminal window. To monitor logs manually, run:"
            echo "tail -f $LOG_FILE_UPLOAD $LOG_FILE_TASKS"
        fi
    fi
}

# Function to start the Celery worker
start_celery() {
    echo "Starting Celery worker..."
    if [ "$DEBUG_MODE" == true ]; then
        celery -A celery_worker.celery worker --loglevel=debug -P threads &
    else
        celery -A celery_worker.celery worker --loglevel=info -P threads &
    fi
    CELERY_PID=$!
    echo "Celery worker started with PID: $CELERY_PID"
}

# Function to start the Flask application
start_flask() {
    echo "Starting Flask app..."
    if [ "$DEBUG_MODE" == true ]; then
        FLASK_ENV=development FLASK_DEBUG=1 python app.py
    else
        python app.py
    fi
}

# ===== Main Execution =====

# Parse command line arguments
parse_args "$@"

# Display banner
show_banner

# Create necessary directories
mkdir -p uploads instance

# Clear log files in debug mode
clear_logs

# Check Redis status
check_redis

# Run diagnostics in debug mode
if [ "$DEBUG_MODE" == true ]; then
    check_celery
    echo "------------------------"
    check_stuck_tasks
    echo "------------------------"
    diagnose_common_issues
    echo "------------------------"
    show_recommendations
    echo "------------------------"
fi

# Start log monitoring in a separate window
start_log_monitoring

# Start Celery worker
start_celery

# Start Flask app
start_flask

# When Flask app is terminated, also terminate Celery worker
echo "Shutting down Celery worker..."
kill $CELERY_PID 2>/dev/null

echo "Application terminated." 