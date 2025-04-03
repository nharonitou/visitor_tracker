# Visitor Tracker Application

A Flask web application for tracking visitors.

## Administrator Guide

For detailed information about the application structure, configuration, troubleshooting, and maintenance, please refer to the [Administrator Guide](ADMIN_GUIDE.md).

## Deployment Instructions

### Option 1: Deploy as a Systemd Service

This method will set up the application as a systemd service that automatically starts when the server boots.

1. Make sure the deployment script is executable:
   ```
   chmod +x deploy.sh
   ```

2. Run the deployment script:
   ```
   ./deploy.sh
   ```

   This script will:
   - Copy all application files to matrix.1stadvantage.org
   - Install required dependencies
   - Set up a systemd service
   - Start the service

3. After deployment, the application will be available at:
   ```
   http://matrix.1stadvantage.org:8080
   ```

4. To manage the service:
   ```
   # Check status
   ssh matrix.1stadvantage.org "sudo systemctl status visitor_tracker"

   # Restart the service
   ssh matrix.1stadvantage.org "sudo systemctl restart visitor_tracker"

   # Stop the service
   ssh matrix.1stadvantage.org "sudo systemctl stop visitor_tracker"

   # View logs
   ssh matrix.1stadvantage.org "sudo journalctl -u visitor_tracker"
   ```

### Option 2: Run with nohup

This method will run the application in the background using nohup, which keeps it running even if you log out.

1. Make sure the nohup script is executable:
   ```
   chmod +x run_with_nohup.sh
   ```

2. Copy the application files to matrix.1stadvantage.org:
   ```
   rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
       ./* zebra@matrix.1stadvantage.org:~/visitor_tracker/
   ```

3. SSH into matrix.1stadvantage.org:
   ```
   ssh zebra@matrix.1stadvantage.org
   ```

4. Install dependencies:
   ```
   cd ~/visitor_tracker
   pip3 install --user -r requirements.txt
   ```

5. Run the application with nohup:
   ```
   ./run_with_nohup.sh
   ```

6. The application will be available at:
   ```
   http://matrix.1stadvantage.org:8080
   ```

7. To check the logs:
   ```
   tail -f ~/visitor_tracker/visitor_tracker.log
   ```

8. To stop the application:
   ```
   kill $(cat ~/visitor_tracker/visitor_tracker.pid | awk '{print $2}')
   ```

## Application Details

- The application runs on port 8080 using Gunicorn WSGI server
- Gunicorn is configured with 3 worker processes for better performance and reliability
- Database connection details are stored in the .env file
- Teams webhook URL can be configured in the .env file

## About Gunicorn

This application uses Gunicorn (Green Unicorn) as the WSGI HTTP server. Gunicorn is a production-ready, widely-used server that's more suitable for production environments than Flask's built-in development server. Benefits include:

- Better performance and stability
- Ability to handle multiple concurrent requests
- Automatic worker process management
- Graceful application reloads

The systemd service and nohup script are both configured to use Gunicorn with 3 worker processes. You can adjust the number of workers based on your server's resources by modifying the `--workers` parameter in both files.
