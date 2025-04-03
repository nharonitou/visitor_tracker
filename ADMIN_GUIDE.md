# Visitor Tracker Application - Administrator Guide

## Overview

The Visitor Tracker is a Flask-based web application that tracks visitors. It allows staff to check in visitors, record their details, and check them out when they leave. 

## Application Structure

```
visitor_tracker/
├── app.py                 # Main Flask application
├── database.py            # Database connection and operations
├── deploy.sh              # Script for deploying to a remote server
├── .env                   # Environment variables and configuration
├── notifications.py       # Teams notification functionality
├── requirements.txt       # Python dependencies
├── run_with_nohup.sh      # Script to run the app with nohup
├── static/                # Static files (CSS, JS, images)
├── templates/             # HTML templates
├── .venv/                 # Python virtual environment
├── visitor_tracker.service # Systemd service file
└── wsgi.py                # WSGI entry point for Gunicorn
```

## Configuration

### Environment Variables (.env)

The application uses the following environment variables, defined in the `.env` file:

```
DB_SERVER=sqlcorp.1stadvantage.org\Warehouse
DB_NAME=Interactions
DB_USERNAME=
DB_PASSWORD=
DB_TABLE=dbo.VisitorInteractions
FLASK_SECRET_KEY=
```

- `DB_SERVER`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`, `DB_TABLE`: Database connection details
- `FLASK_SECRET_KEY`: Secret key for Flask session security

### Systemd Service Configuration

The application runs as a systemd service, configured in `/etc/systemd/system/visitor_tracker.service`:

[Unit]
Description=Visitor Tracker Flask Application
After=network.target

[Service]
User=zebra
WorkingDirectory=/home/zebra/visitor_tracker
ExecStart=/home/zebra/visitor_tracker/.venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8080 wsgi:app
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

This configuration:
- Runs the application as the `zebra` user
- Sets the working directory to `/home/zebra/visitor_tracker`
- Uses Gunicorn from the virtual environment with 3 worker processes
- Binds to all interfaces (0.0.0.0) on port 8080
- Automatically restarts the service if it fails
- Starts the service at system boot

## Dependencies

The application requires the following Python packages:
- Flask: Web framework
- pyodbc: SQL Server database connection
- python-dotenv: Environment variable management
- datetime: Date and time handling
- requests: HTTP requests (for Teams notifications)
- gunicorn: WSGI HTTP server

Additionally, the system requires:
- ODBC Driver 17 for SQL Server: For database connectivity

## Service Management

### Checking Service Status

```bash
systemctl status visitor_tracker.service
```

This will show if the service is running, any recent logs, and process information.

### Starting the Service

```bash
sudo systemctl start visitor_tracker.service
```

### Stopping the Service

```bash
sudo systemctl stop visitor_tracker.service
```

### Restarting the Service

```bash
sudo systemctl restart visitor_tracker.service
```

### Enabling the Service (to start at boot)

```bash
sudo systemctl enable visitor_tracker.service
```

### Disabling the Service (to not start at boot)

```bash
sudo systemctl disable visitor_tracker.service
```

### Viewing Service Logs

```bash
journalctl -u visitor_tracker.service
```

To see only the most recent logs:

```bash
journalctl -u visitor_tracker.service -n 100
```

To follow the logs in real-time:

```bash
journalctl -u visitor_tracker.service -f
```

## Alternative: Running with nohup

Can also run the application using the `run_with_nohup.sh` script:

```bash
cd /home/zebra/visitor_tracker
chmod +x run_with_nohup.sh
./run_with_nohup.sh
```

This will:
- Start the application with Gunicorn
- Run it in the background using nohup
- Log output to `visitor_tracker.log`
- Save the process ID to `visitor_tracker.pid`

To stop the application when running with nohup:

```bash
kill $(cat /home/zebra/visitor_tracker/visitor_tracker.pid | awk '{print $2}')
```

## Troubleshooting

### Service Won't Start

1. Check the service logs:
   ```bash
   journalctl -u visitor_tracker.service -n 50
   ```

2. Verify the virtual environment exists and has Gunicorn installed:
   ```bash
   ls -la /home/zebra/visitor_tracker/.venv/bin/gunicorn
   ```

3. Check if the port is already in use:
   ```bash
   ss -tuln | grep 8080
   ```

4. Verify the database connection:
   ```bash
   cd /home/zebra/visitor_tracker
   source .venv/bin/activate
   python -c "import database; print(database.create_connection())"
   ```

### Database Connection Issues

1. Verify the .env file has the correct database credentials:
   ```bash
   cat /home/zebra/visitor_tracker/.env
   ```

2. Check if the ODBC driver is installed:
   ```bash
   odbcinst -q -d
   ```

3. Test the database connection manually:
   ```bash
   cd /home/zebra/visitor_tracker
   source .venv/bin/activate
   python -c "import pyodbc; conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=sqlcorp.1stadvantage.org\\Warehouse;DATABASE=Interactions;UID=bidataaccess;PWD=JP6w0*YN#uq);Encrypt=No;TrustServerCertificate=Yes;'; conn = pyodbc.connect(conn_str); print('Connection successful')"
   ```

### Application Errors

1. Check the application logs:
   ```bash
   journalctl -u visitor_tracker.service
   ```

2. If running with nohup, check the log file:
   ```bash
   tail -f /home/zebra/visitor_tracker/visitor_tracker.log
   ```

## Reinstalling or Updating the Application

### Updating the Code

1. Update the code in `/home/zebra/visitor_tracker`
2. Restart the service:
   ```bash
   sudo systemctl restart visitor_tracker.service
   ```

### Reinstalling Dependencies

1. Activate the virtual environment:
   ```bash
   cd /home/zebra/visitor_tracker
   source .venv/bin/activate
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Restart the service:
   ```bash
   sudo systemctl restart visitor_tracker.service
   ```

### Recreating the Virtual Environment

If the virtual environment becomes corrupted:

1. Stop the service:
   ```bash
   sudo systemctl stop visitor_tracker.service
   ```

2. Remove the old virtual environment:
   ```bash
   rm -rf /home/zebra/visitor_tracker/.venv
   ```

3. Create a new virtual environment:
   ```bash
   cd /home/zebra/visitor_tracker
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Start the service:
   ```bash
   sudo systemctl start visitor_tracker.service
   ```

## Backup and Restore

### Backing Up the Application

To back up the application:

```bash
cd /home/zebra
tar -czvf visitor_tracker_backup_$(date +%Y%m%d).tar.gz visitor_tracker
```

This creates a compressed archive of the entire application directory.

### Restoring from Backup

To restore from a backup:

1. Stop the service:
   ```bash
   sudo systemctl stop visitor_tracker.service
   ```

2. Extract the backup:
   ```bash
   cd /home/zebra
   tar -xzvf visitor_tracker_backup_YYYYMMDD.tar.gz
   ```

3. Start the service:
   ```bash
   sudo systemctl start visitor_tracker.service
   ```

## Security Considerations

- The `.env` file contains sensitive database credentials. Ensure it has restricted permissions:
  ```bash
  chmod 600 /home/zebra/visitor_tracker/.env
  ```

- The application binds to all interfaces (0.0.0.0). Consider using a firewall to restrict access to port 8080.

- Regularly update the application dependencies to address security vulnerabilities:
  ```bash
  cd /home/zebra/visitor_tracker
  source .venv/bin/activate
  pip install --upgrade -r requirements.txt
  ```

## Contact Information

For issues with the Visitor Tracker application, contact:
- IT Department: [Add contact information]
- Application Developer: [Add contact information]
