#!/bin/bash

# Exit on error
set -e

# Variables
APP_DIR="/home/$(whoami)/visitor_tracker"
LOG_FILE="$APP_DIR/visitor_tracker.log"

echo "=== Starting Visitor Tracker with nohup ==="

# Change to the application directory
cd $APP_DIR

# Activate virtual environment if you have one
source .venv/bin/activate

# Start the application with nohup and gunicorn
echo "Starting application with Gunicorn on port 8080..."
nohup .venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8080 wsgi:app > $LOG_FILE 2>&1 &

# Get the process ID
PID=$!
echo "Application started with PID: $PID"
echo "PID $PID" > "$APP_DIR/visitor_tracker.pid"

echo "=== Application is now running in the background ==="
echo "You can view the logs with: tail -f $LOG_FILE"
echo "To stop the application: kill $(cat $APP_DIR/visitor_tracker.pid | awk '{print $2}')"
