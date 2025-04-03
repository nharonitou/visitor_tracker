# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import os
import logging
from dotenv import load_dotenv
from datetime import datetime

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

@app.route('/', methods=['GET', 'POST'])
def visitor_form():
    form_data_on_error = {} # Store submitted data if validation fails
    
    # Get available badges (filter out badges that are already checked in)
    checked_in_badges, error = database.get_checked_in_badges()
    if error:
        logging.error(f"Error getting checked-in badges: {error}")
        checked_in_badges = []
    
    # Filter out badges that are already in use
    available_badges = [badge for badge in BADGE_NUMBERS if badge not in checked_in_badges]
    
    if request.method == 'POST':
        # Get data from form, store in dict
        visitor_details = {
            'GuestFirstName': request.form.get('guest_first_name','').strip(),
            'GuestLastName': request.form.get('guest_last_name','').strip(),
            'VisitorType': request.form.get('visitor_type'),
            'Branch': request.form.get('branch'),
            'DepartmentVisited': request.form.get('department'),
            'VendorName': request.form.get('vendor_name','').strip(),
            'BadgeNumber': request.form.get('badge_number'),
            'HostEmployeeName': request.form.get('here_to_see','').strip(),
            'Comments': request.form.get('comments','').strip()
        }
        form_data_on_error = visitor_details # Keep data for re-rendering form on error

        # Basic Server-Side Validation
        required_fields = ['GuestFirstName', 'GuestLastName', 'VisitorType', 'Branch', 'DepartmentVisited', 'BadgeNumber', 'HostEmployeeName']
        missing_fields = [field for field in required_fields if not visitor_details.get(field)]

        if missing_fields:
            flash(f"Error: Missing required fields: {', '.join(missing_fields)}", 'danger')
            # Re-render form with submitted data and errors
            return render_template('visitor_form.html',
                                   visitor_types=VISITOR_TYPES, branches=BRANCHES,
                                   departments=DEPARTMENTS, badge_numbers=available_badges,
                                   visitor=form_data_on_error) # Pass back entered data

        # --- Add to Database ---
        logging.info(f"Attempting to add visitor: {visitor_details.get('GuestLastName')}")
        success, db_message = database.add_visitor(visitor_details)

        if success:
            logging.info(f"Successfully added visitor: {visitor_details.get('GuestLastName')}")
            flash('Visitor checked in successfully!', 'success')

            # --- Attempt to Send Teams Notification (after successful DB insert ... still need webhook, can't create) ---
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

        else:
            # Database add failed
            logging.error(f"Database error adding visitor: {db_message}")
            flash(f'Error adding visitor: {db_message}', 'danger')
            # Re-render form with existing data
            return render_template('visitor_form.html',
                                   visitor_types=VISITOR_TYPES, branches=BRANCHES,
                                   departments=DEPARTMENTS, badge_numbers=available_badges,
                                   visitor=form_data_on_error) # Pass back entered data

    # GET request: Show the blank form
    return render_template('visitor_form.html',
                           visitor_types=VISITOR_TYPES, branches=BRANCHES,
                           departments=DEPARTMENTS, badge_numbers=available_badges,
                           visitor=form_data_on_error) # Pass empty dict or prior data if error reload

@app.route('/records')
def view_records():
    """Displays the list of visitor records."""
    logging.info("Fetching visitor records")
    visitors, error = database.get_all_visitors()

    if error:
        logging.error(f"Error retrieving records: {error}")
        flash(f"Error retrieving records: {error}", 'danger')
        visitors = [] # Show empty list on error

    # No need to format dates here if Jinja does it... maybe
    return render_template('records.html', visitors=visitors)

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

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)
