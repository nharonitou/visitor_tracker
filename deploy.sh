#!/bin/bash

# Exit on error
set -e

# Variables
REMOTE_HOST="matrix.1stadvantage.org"
REMOTE_USER="$USER"  # Use the current user, change if needed
APP_DIR="/home/$REMOTE_USER/visitor_tracker"
SERVICE_NAME="visitor_tracker"

echo "=== Deploying Visitor Tracker to $REMOTE_HOST ==="

# 1. Create a directory on the remote server if it doesn't exist
echo "Creating application directory on $REMOTE_HOST..."
ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $APP_DIR"

# 2. Copy application files to the remote server
echo "Copying application files to $REMOTE_HOST..."
rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
    ./* $REMOTE_USER@$REMOTE_HOST:$APP_DIR/

# 3. Install dependencies on the remote server
echo "Installing dependencies on $REMOTE_HOST..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $APP_DIR && pip3 install --user -r requirements.txt"

# Verify Gunicorn is installed and accessible
echo "Verifying Gunicorn installation..."
ssh $REMOTE_USER@$REMOTE_HOST "which ~/.local/bin/gunicorn || echo 'WARNING: Gunicorn not found in ~/.local/bin/'"

# 4. Copy the systemd service file to the appropriate location
echo "Setting up systemd service..."
ssh $REMOTE_USER@$REMOTE_HOST "sudo cp $APP_DIR/visitor_tracker.service /etc/systemd/system/ && \
    sudo systemctl daemon-reload && \
    sudo systemctl enable $SERVICE_NAME"

# 5. Start the service
echo "Starting the service..."
ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl start $SERVICE_NAME"

# 6. Check the service status
echo "Checking service status..."
ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl status $SERVICE_NAME"

echo "=== Deployment completed successfully ==="
echo "Your application is now running at http://$REMOTE_HOST:8080"
