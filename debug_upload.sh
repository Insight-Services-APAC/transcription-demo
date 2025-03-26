#!/bin/bash

# Clear existing log files
echo "Clearing existing log files..."
> upload_debug.log
> transcription_tasks.log

# Set up monitoring function
monitor_logs() {
    echo "=== Monitoring logs for upload and processing (press Ctrl+C to stop) ==="
    echo "=== Watching for 'Processing file, please wait...' sticking point ==="
    echo ""
    
    # Use tail to monitor both log files simultaneously
    tail -f upload_debug.log transcription_tasks.log | grep --color=auto -E "error|ERROR|fail|FAIL|exception|Exception|Processing file, please wait|Starting transcription"
}

# Function to check Celery worker status
check_celery() {
    echo "=== Checking Celery worker status ==="
    ps aux | grep -i celery | grep -v grep
    
    echo ""
    echo "=== Checking Redis connection ==="
    redis-cli ping
    redis-cli info | grep connected
    
    echo ""
    echo "=== Checking Redis queue status ==="
    redis-cli llen celery
    redis-cli type celery
}

# Function to check for stuck tasks
check_stuck_tasks() {
    echo "=== Checking database for stuck tasks ==="
    
    echo "Files with status 'processing':"
    sqlite3 instance/app.db "SELECT id, filename, status, current_stage, progress_percent, upload_time FROM file WHERE status = 'processing';"
    
    echo ""
    echo "Files with errors:"
    sqlite3 instance/app.db "SELECT id, filename, status, error_message, upload_time FROM file WHERE status = 'error';"
}

# Function to diagnose common issues
diagnose_common_issues() {
    echo "=== Diagnosing common issues ==="
    
    echo "Checking disk space:"
    df -h
    
    echo ""
    echo "Checking memory usage:"
    free -h
    
    echo ""
    echo "Checking for Azure connection issues:"
    grep -i "azure\|blob\|storage" upload_debug.log transcription_tasks.log | grep -i "error\|fail\|exception"
    
    echo ""
    echo "Checking for file size issues:"
    grep -i "size\|bytes\|mb\|gb" upload_debug.log transcription_tasks.log
    
    echo ""
    echo "Checking for timeouts or slow operations:"
    grep -i "timeout\|seconds\|complete" upload_debug.log transcription_tasks.log | grep -i "seconds\|time"
}

# Function to show recommended next steps
show_recommendations() {
    echo "=== Troubleshooting Recommendations ==="
    echo ""
    echo "1. If celery worker is not running, start it with:"
    echo "   celery -A celery_worker.celery worker --loglevel=info -P threads"
    echo ""
    echo "2. If Redis is not running, start it with:"
    echo "   redis-server"
    echo ""
    echo "3. If files are stuck in 'processing' state, check:"
    echo "   - Network connectivity to Azure"
    echo "   - Azure credentials and permissions"
    echo "   - Available disk space for temporary files"
    echo "   - Memory usage for large file processing"
    echo ""
    echo "4. To reset a stuck file, run:"
    echo "   sqlite3 instance/app.db \"UPDATE file SET status = 'uploaded', current_stage = NULL, progress_percent = 0 WHERE id = '<file_id>';\""
    echo ""
    echo "5. To view detailed logs, run:"
    echo "   tail -f upload_debug.log"
    echo "   tail -f transcription_tasks.log"
    echo ""
}

# Main execution
echo "===== UPLOAD DEBUGGING TOOL ====="
echo "This script will help diagnose issues with file uploads and processing"
echo ""

# Run diagnostics
check_celery
echo "------------------------"
check_stuck_tasks
echo "------------------------"
diagnose_common_issues
echo "------------------------"
show_recommendations
echo "------------------------"

# Start monitoring logs
monitor_logs 