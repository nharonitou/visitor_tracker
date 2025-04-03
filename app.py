# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, Response
import os
import logging
import csv
import io
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Import database functions and the new notifications function
import database
from notifications import send_teams_notification

# Load environment variables from .env file
load_dotenv()

# Configure basic logging (do this once)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'change_this_in_production') 

VISITOR_TYPES = ['Contractor', 'Family', 'Food Delivery', 'Meeting', 'Vendor']
BRANCHES = ['Kiln Creek', '1A University']
DEPARTMENTS = [
    '1AU', 'Advantage Financial', 'Business Development', 'Business Services',
    'Compliance', 'Consumer Lending', 'Debt Resolution', 'Deposit Operations',
    'E-Branch', 'Executives', 'Facilities', 'Financial Accounting',
    'Human Resources', 'Internal Audit', 'Marketing', 'Mortgages', 'N/A',
    'Project Management', 'Retail', 'Technology', 'Training'
]
BADGE_NUMBERS = [str(i) for i in range(56863, 56873)]


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.context_processor
def inject_visitor_count():
    """Inject the current visitor count into all templates."""
    count, error = database.get_current_visitor_count()
    if error:
        logging.error(f"Error getting visitor count: {error}")
        count = 0
    return {'current_visitor_count': count}

# --- Routes ---

@app.route('/')
def index():
    """Landing page with options for advanced or internal check-in."""
    return render_template('index.html')

@app.route('/internal-checkin', methods=['GET', 'POST'])
def visitor_form():
    form_data_on_error = {} # Store submitted data if validation fails
    
    # Get available badges (filter out badges that are already checked in)
    checked_in_badges, error = database.get_checked_in_badges()
    if error:
        logging.error(f"Error getting checked-in badges: {error}")
        checked_in_badges = []
    
    # Filter out badges that are already in use
    available_badges = [badge for badge in BADGE_NUMBERS if badge not in checked_in_badges]
    
    # Get pending visitors for the pre-registered visitors modal
    pending_visitors, pending_error = database.get_pending_visitors()
    if pending_error:
        logging.error(f"Error retrieving pending visitors: {pending_error}")
        flash(f"Error retrieving pending visitors: {pending_error}", 'danger')
        pending_visitors = [] # Show empty list on error
    
    # Check if a pending_id was provided in the URL
    pending_id = request.args.get('pending_id')
    visitor = {}
    
    # If pending_id is provided, get the visitor details to pre-populate the form
    if pending_id:
        for pending_visitor in pending_visitors:
            if str(pending_visitor['VisitorID']) == str(pending_id):
                visitor = pending_visitor
                # Set the check-in type to immediate
                visitor['check_in_type'] = 'immediate'
                break
    
    if request.method == 'POST':
        # Determine if this is an immediate check-in or advanced check-in
        check_in_type = request.form.get('check_in_type', 'immediate')
        is_advanced = (check_in_type == 'advanced')
        
        # Get common data from form
        visitor_details = {
            'GuestFirstName': request.form.get('guest_first_name','').strip(),
            'GuestLastName': request.form.get('guest_last_name','').strip(),
            'VisitorType': request.form.get('visitor_type'),
            'Branch': request.form.get('branch'),
            'DepartmentVisited': request.form.get('department'),
            'VendorName': request.form.get('vendor_name','').strip(),
            'HostEmployeeName': request.form.get('here_to_see','').strip(),
            'Comments': request.form.get('comments','').strip()
        }
        
        # Add advanced check-in specific fields if applicable
        if is_advanced:
            visitor_details.update({
                'BadgeNumber': 'No Badge',  # No badge for advanced check-in
                'ColleagueFirstName': request.form.get('colleague_first_name', '').strip(),
                'ColleagueLastName': request.form.get('colleague_last_name', '').strip(),
                'AdvanceCheckInTime': request.form.get('advance_checkin_time'),
                'IsAdvanceCheckIn': True,
                'SubmitterIPAddress': request.remote_addr
            })
        else:
            visitor_details['BadgeNumber'] = request.form.get('badge_number')
        
        form_data_on_error = visitor_details # Keep data for re-rendering form on error

        # Basic Server-Side Validation - different required fields based on check-in type
        if is_advanced:
            required_fields = [
                'GuestFirstName', 'GuestLastName', 'VisitorType', 'Branch', 
                'DepartmentVisited', 'HostEmployeeName', 'ColleagueFirstName', 
                'ColleagueLastName', 'AdvanceCheckInTime'
            ]
        else:
            required_fields = [
                'GuestFirstName', 'GuestLastName', 'VisitorType', 'Branch', 
                'DepartmentVisited', 'BadgeNumber', 'HostEmployeeName'
            ]
            
        missing_fields = [field for field in required_fields if not visitor_details.get(field)]

        if missing_fields:
            flash(f"Error: Missing required fields: {', '.join(missing_fields)}", 'danger')
            # Re-render form with submitted data and errors
            return render_template('visitor_form.html',
                                   visitor_types=VISITOR_TYPES, branches=BRANCHES,
                                   departments=DEPARTMENTS, badge_numbers=available_badges,
                                   visitor=form_data_on_error, # Pass back entered data
                                   pending_visitors=pending_visitors) # Pass pending visitors for the modal

        # --- Add to Database ---
        if is_advanced:
            logging.info(f"Attempting to add advanced check-in visitor: {visitor_details.get('GuestLastName')}")
            success, db_message = database.add_advanced_visitor(visitor_details)
            
            if success:
                logging.info(f"Successfully added advanced check-in visitor: {visitor_details.get('GuestLastName')}")
                flash('Visitor pre-registered successfully!', 'success')
                return redirect(url_for('index'))
        else:
            logging.info(f"Attempting to add visitor: {visitor_details.get('GuestLastName')}")
            success, db_message = database.add_visitor(visitor_details)
            
            if success:
                logging.info(f"Successfully added visitor: {visitor_details.get('GuestLastName')}")
                flash('Visitor checked in successfully!', 'success')

                # --- Attempt to Send Teams Notification (after successful DB insert) ---
                logging.info(f"Attempting to send Teams notification for {visitor_details.get('GuestLastName')}")
                try:
                    # Don't let notification failure break the user flow
                    notification_sent = send_teams_notification(visitor_details)
                    if not notification_sent:
                         # Optionally flash a less severe message if notification fails
                         # flash('Visitor checked in, but notification could not be sent.', 'warning')
                         pass # Already logged in the notification function
                except Exception as e:
                    # Catch any unexpected errors from the notification function itself
                    logging.error(f"Error calling send_teams_notification function: {e}", exc_info=True)
                    # flash('Visitor checked in, but an error occurred sending the notification.', 'warning')

                # --- Redirect after DB success, regardless of notification outcome ---
                return redirect(url_for('view_records'))

        # If we get here, there was a database error
        if not success:
            logging.error(f"Database error adding visitor: {db_message}")
            flash(f'Error adding visitor: {db_message}', 'danger')
            # Re-render form with existing data
            return render_template('visitor_form.html',
                                   visitor_types=VISITOR_TYPES, branches=BRANCHES,
                                   departments=DEPARTMENTS, badge_numbers=available_badges,
                                   visitor=form_data_on_error, # Pass back entered data
                                   pending_visitors=pending_visitors) # Pass pending visitors for the modal

    # GET request: Show the blank form
    return render_template('visitor_form.html',
                           visitor_types=VISITOR_TYPES, branches=BRANCHES,
                           departments=DEPARTMENTS, badge_numbers=available_badges,
                           visitor=form_data_on_error, # Pass empty dict or prior data if error reload
                           pending_visitors=pending_visitors) # Pass pending visitors for the modal

@app.route('/records')
def view_records():
    """Displays the list of visitor records and pending visitors."""
    logging.info("Fetching visitor records")
    visitors, error = database.get_all_visitors()
    pending_visitors, pending_error = database.get_pending_visitors()

    if error:
        logging.error(f"Error retrieving records: {error}")
        flash(f"Error retrieving records: {error}", 'danger')
        visitors = [] # Show empty list on error
        
    if pending_error:
        logging.error(f"Error retrieving pending visitors: {pending_error}")
        flash(f"Error retrieving pending visitors: {pending_error}", 'danger')
        pending_visitors = [] # Show empty list on error

    # Get available badges (filter out badges that are already checked in)
    checked_in_badges, badge_error = database.get_checked_in_badges()
    if badge_error:
        logging.error(f"Error getting checked-in badges: {badge_error}")
        checked_in_badges = []
    
    # Filter out badges that are already in use
    available_badges = [badge for badge in BADGE_NUMBERS if badge not in checked_in_badges]
    available_badges.insert(0, "No Badge")  # Add "No Badge" option

    # No need to format dates here if Jinja does it... maybe
    return render_template('records.html', 
                          visitors=visitors, 
                          pending_visitors=pending_visitors,
                          badge_numbers=available_badges)

@app.route('/checkin-pending/<int:visitor_id>', methods=['POST'])
def checkin_pending(visitor_id):
    """Handles checking in a pre-registered visitor."""
    badge_number = request.form.get('badge_number')
    
    if not badge_number:
        flash('Please select a badge number', 'warning')
        return redirect(url_for('view_records'))
    
    logging.info(f"Attempting to check in pending visitor ID: {visitor_id} with badge: {badge_number}")
    success, message = database.checkin_pending_visitor(visitor_id, badge_number)

    if success:
        logging.info(f"Successfully checked in pending visitor ID: {visitor_id}")
        flash(message, 'success')
    else:
        logging.warning(f"Failed to check in pending visitor ID {visitor_id}: {message}")
        flash(f'Error checking in: {message}', 'warning')

    return redirect(url_for('view_records'))

@app.route('/checkout/<int:visitor_id>', methods=['POST'])
def checkout(visitor_id):
    """Handles the checkout action."""
    logging.info(f"Attempting to check out visitor ID: {visitor_id}")
    success, message = database.checkout_visitor(visitor_id)

    if success:
        logging.info(f"Successfully checked out visitor ID: {visitor_id}")
        flash(message, 'success')
    else:
        # Log specific message (could be 'not found' or 'db error')
        logging.warning(f"Failed to checkout visitor ID {visitor_id}: {message}")
        flash(f'Error checking out: {message}', 'warning') # Use warning as it might not be a critical db error

    return redirect(url_for('view_records')) # Redirect back to the records page

# Advanced check-in functionality has been integrated into the visitor_form route

@app.route('/vendor-portal', methods=['GET', 'POST'])
def vendor_portal():
    """Vendor portal for pre-registering visits."""
    if request.method == 'POST':
        # Get data from form
        visitor_details = {
            'GuestFirstName': request.form.get('guest_first_name', '').strip(),
            'GuestLastName': request.form.get('guest_last_name', '').strip(),
            'VisitorType': request.form.get('visitor_type'),
            'Branch': request.form.get('branch'),
            'DepartmentVisited': request.form.get('department'),
            'VendorName': request.form.get('vendor_name', '').strip(),
            'BadgeNumber': 'No Badge',  # No badge for advanced check-in
            'HostEmployeeName': request.form.get('here_to_see', '').strip(),
            'Comments': request.form.get('comments', '').strip(),
            'ColleagueFirstName': 'Vendor',  # Mark as vendor registration
            'ColleagueLastName': 'Portal',   # Mark as vendor registration
            'AdvanceCheckInTime': request.form.get('advance_checkin_time'),
            'IsAdvanceCheckIn': True,
            'SubmitterIPAddress': request.remote_addr
        }

        # Basic Server-Side Validation
        required_fields = [
            'GuestFirstName', 'GuestLastName', 'VisitorType', 'Branch', 
            'DepartmentVisited', 'HostEmployeeName', 'VendorName', 'AdvanceCheckInTime'
        ]
        missing_fields = [field for field in required_fields if not visitor_details.get(field)]

        if missing_fields:
            flash(f"Error: Missing required fields: {', '.join(missing_fields)}", 'danger')
            # Re-render form with error
            return render_template('vendor_portal.html',
                                  visitor_types=VISITOR_TYPES, branches=BRANCHES,
                                  departments=DEPARTMENTS)

        # Add to Database
        logging.info(f"Attempting to add vendor pre-registration: {visitor_details.get('GuestLastName')}")
        success, db_message = database.add_advanced_visitor(visitor_details)

        if success:
            logging.info(f"Successfully added vendor pre-registration: {visitor_details.get('GuestLastName')}")
            # Show success message
            return render_template('vendor_success.html', 
                                  visitor=visitor_details,
                                  scheduled_time=datetime.fromisoformat(visitor_details.get('AdvanceCheckInTime').replace('Z', '+00:00')))
        else:
            # Database add failed
            logging.error(f"Database error adding vendor pre-registration: {db_message}")
            flash(f'Error registering visit: {db_message}', 'danger')
            # Re-render form with error
            return render_template('vendor_portal.html',
                                  visitor_types=VISITOR_TYPES, branches=BRANCHES,
                                  departments=DEPARTMENTS)

    # GET request: Show the blank form
    return render_template('vendor_portal.html',
                          visitor_types=VISITOR_TYPES, branches=BRANCHES,
                          departments=DEPARTMENTS)

@app.route('/export-csv', methods=['POST'])
def export_csv():
    """Exports visitor records to CSV based on date range."""
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not start_date or not end_date:
            flash('Please provide both start and end dates', 'warning')
            return redirect(url_for('view_records'))
        
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Add one day to end_date to include the entire end date
        end_date = end_date + timedelta(days=1)
        
        # Get records within date range
        visitors, error = database.get_visitors_by_date_range(start_date, end_date)
        
        if error:
            logging.error(f"Error retrieving records for export: {error}")
            flash(f"Error retrieving records: {error}", 'danger')
            return redirect(url_for('view_records'))
        
        if not visitors:
            flash("No records found in the selected date range", 'warning')
            return redirect(url_for('view_records'))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row
        header = [
            'Visitor ID', 'First Name', 'Last Name', 'Type', 'Host', 
            'Department', 'Branch', 'Badge', 'Check-In Time', 
            'Check-Out Time', 'Status', 'Vendor Name', 'Comments',
            'Registered By First Name', 'Registered By Last Name', 
            'Expected Check-In Time', 'Submission Time', 'Is Pre-registered', 'Submitter IP'
        ]
        writer.writerow(header)
        
        # Write data rows
        for visitor in visitors:
            check_in_time = visitor['CheckInTime'].strftime('%m/%d/%Y %I:%M %p') if visitor['CheckInTime'] else 'N/A'
            check_out_time = visitor['CheckOutTime'].strftime('%m/%d/%Y %I:%M %p') if visitor['CheckOutTime'] else 'N/A'
            advance_checkin_time = visitor['AdvanceCheckInTime'].strftime('%m/%d/%Y %I:%M %p') if visitor.get('AdvanceCheckInTime') else 'N/A'
            submission_time = visitor['SubmissionTime'].strftime('%m/%d/%Y %I:%M %p') if visitor.get('SubmissionTime') else 'N/A'
            
            row = [
                visitor['VisitorID'],
                visitor['GuestFirstName'],
                visitor['GuestLastName'],
                visitor['VisitorType'],
                visitor['HostEmployeeName'],
                visitor['DepartmentVisited'],
                visitor['Branch'],
                visitor['BadgeNumber'],
                check_in_time,
                check_out_time,
                'Checked In' if visitor['Status'] == 'CheckedIn' else 'Checked Out' if visitor['Status'] == 'CheckedOut' else visitor['Status'],
                visitor['VendorName'] or 'N/A',
                visitor['Comments'] or 'N/A',
                visitor.get('ColleagueFirstName') or 'N/A',
                visitor.get('ColleagueLastName') or 'N/A',
                advance_checkin_time,
                submission_time,
                'Yes' if visitor.get('IsAdvanceCheckIn') else 'No',
                visitor.get('SubmitterIPAddress') or 'N/A'
            ]
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        filename = f"visitor_records_{start_date.strftime('%Y%m%d')}_to_{(end_date - timedelta(days=1)).strftime('%Y%m%d')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
        
    except Exception as e:
        logging.error(f"Error exporting CSV: {str(e)}")
        flash(f"Error exporting CSV: {str(e)}", 'danger')
        return redirect(url_for('view_records'))

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)
