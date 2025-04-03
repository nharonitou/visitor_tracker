import pyodbc
import os
import logging
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()

DB_SERVER = os.getenv('DB_SERVER')
DB_NAME = os.getenv('DB_NAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_TABLE = os.getenv('DB_TABLE') 


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_connection():
    """Creates and returns a connection to the SQL Server database."""
    conn_str = (
        r'DRIVER={ODBC Driver 17 for SQL Server};' 
        r'SERVER=' + DB_SERVER + ';'
        r'DATABASE=' + DB_NAME + ';'
        r'UID=' + DB_USERNAME + ';'
        r'PWD=' + DB_PASSWORD + ';'
        r'Encrypt=No;' # Yes in production if SSL is configured ???
        r'TrustServerCertificate=Yes;' # Add if self-signed cert or encryption without full validation ????
    )
    logging.info(f"Attempting to connect to database: {DB_SERVER}/{DB_NAME}")
    try:
        conn = pyodbc.connect(conn_str, autocommit=False) 
        logging.info("Database connection successful")
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {str(e)}")
        # Consider how to handle this - maybe raise it or return None
        # For a web app, failing requests might be better than crashing
        return None # Or raise e ?? will figure out later 

def add_visitor(visitor_data):
    """Adds a new visitor record to the database."""
    conn = create_connection()
    if not conn:
        return False, "Database connection failed"

    cursor = conn.cursor()

    sql = f"""
        INSERT INTO {DB_TABLE} (
            GuestFirstName, GuestLastName, VisitorType, Branch, DepartmentVisited,
            VendorName, BadgeNumber, HostEmployeeName, Comments, CheckInTime, Status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 'CheckedIn')
    """
    params = (
        visitor_data.get('GuestFirstName'),
        visitor_data.get('GuestLastName'),
        visitor_data.get('VisitorType'),
        visitor_data.get('Branch'),
        visitor_data.get('DepartmentVisited'),
        visitor_data.get('VendorName'),
        visitor_data.get('BadgeNumber'),
        visitor_data.get('HostEmployeeName'), # "Here to see"
        visitor_data.get('Comments')
    )

    try:
        logging.info(f"Executing SQL: {sql} with params: {params}")
        cursor.execute(sql, params)
        conn.commit() # Commit the transaction
        logging.info("Visitor added successfully.")
        return True, "Visitor added successfully."
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to add visitor. SQLSTATE: {sqlstate} Message: {message}")
        conn.rollback() # Rollback on error
        return False, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        conn.rollback()
        return False, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
def get_current_visitor_count():
    """Returns the count of visitors currently checked in."""
    conn = create_connection()
    if not conn:
        return 0, "Database connection failed"

    cursor = conn.cursor()
    sql = f"""
        SELECT COUNT(*) AS CurrentVisitors
        FROM {DB_TABLE}
        WHERE Status = 'CheckedIn'
    """
    try:
        cursor.execute(sql)
        count = cursor.fetchone()[0]
        logging.info(f"Current visitor count: {count}")
        return count, None
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to get visitor count. SQLSTATE: {sqlstate} Message: {message}")
        return 0, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred while getting visitor count: {str(e)}")
        return 0, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
def get_checked_in_badges():
    """Returns a list of badge numbers that are currently checked in."""
    conn = create_connection()
    if not conn:
        return [], "Database connection failed"

    cursor = conn.cursor()
    sql = f"""
        SELECT BadgeNumber
        FROM {DB_TABLE}
        WHERE Status = 'CheckedIn'
    """
    try:
        cursor.execute(sql)
        badges = [row[0] for row in cursor.fetchall()]
        logging.info(f"Retrieved {len(badges)} checked-in badges")
        return badges, None
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to get checked-in badges. SQLSTATE: {sqlstate} Message: {message}")
        return [], f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred while getting checked-in badges: {str(e)}")
        return [], f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_all_visitors():
    """Retrieves all visitor records (excluding pending visitors), ordered by CheckInTime descending."""
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    cursor = conn.cursor()
    visitors = []
    sql = f"""
        SELECT
            VisitorID, GuestFirstName, GuestLastName, VisitorType, Branch, DepartmentVisited,
            VendorName, BadgeNumber, HostEmployeeName, Comments,
            CheckInTime, CheckOutTime, Status
        FROM {DB_TABLE}
        WHERE Status != 'Pending'
        ORDER BY CheckInTime DESC
    """
    try:
        cursor.execute(sql)
        # Get column names from cursor description
        columns = [column[0] for column in cursor.description]
        # Fetch rows and convert to list of dictionaries
        visitors = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logging.info(f"Retrieved {len(visitors)} visitor records.")
        return visitors, None
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to retrieve visitors. SQLSTATE: {sqlstate} Message: {message}")
        return None, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching visitors: {str(e)}")
        return None, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_visitors_by_date_range(start_date, end_date):
    """Retrieves visitor records within a specified date range."""
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    cursor = conn.cursor()
    visitors = []
    sql = f"""
        SELECT
            VisitorID, GuestFirstName, GuestLastName, VisitorType, Branch, DepartmentVisited,
            VendorName, BadgeNumber, HostEmployeeName, Comments,
            CheckInTime, CheckOutTime, Status, ColleagueFirstName, ColleagueLastName,
            AdvanceCheckInTime, SubmissionTime, IsAdvanceCheckIn, SubmitterIPAddress
        FROM {DB_TABLE}
        WHERE CheckInTime BETWEEN ? AND ?
        ORDER BY CheckInTime DESC
    """
    params = (start_date, end_date)
    
    try:
        cursor.execute(sql, params)
        # Get column names from cursor description
        columns = [column[0] for column in cursor.description]
        # Fetch rows and convert to list of dictionaries
        visitors = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logging.info(f"Retrieved {len(visitors)} visitor records between {start_date} and {end_date}.")
        return visitors, None
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to retrieve visitors by date range. SQLSTATE: {sqlstate} Message: {message}")
        return None, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching visitors by date range: {str(e)}")
        return None, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def checkout_visitor(visitor_id):
    """Updates a visitor's status to 'CheckedOut' and sets the CheckOutTime."""
    conn = create_connection()
    if not conn:
        return False, "Database connection failed"

    cursor = conn.cursor()
    sql = f"""
        UPDATE {DB_TABLE}
        SET Status = 'CheckedOut', CheckOutTime = GETDATE()
        WHERE VisitorID = ? AND Status = 'CheckedIn'
    """
    params = (visitor_id,)

    try:
        logging.info(f"Checking out visitor ID: {visitor_id}")
        cursor.execute(sql, params)
        # Check if any row was actually updated
        if cursor.rowcount == 0:
            conn.rollback() # Rollback if no rows affected (already checked out or invalid ID)
            logging.warning(f"Visitor ID {visitor_id} not found or already checked out.")
            return False, "Visitor not found or already checked out."

        conn.commit() # Commit the transaction
        logging.info(f"Visitor ID {visitor_id} checked out successfully.")
        return True, "Visitor checked out successfully."
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to check out visitor ID {visitor_id}. SQLSTATE: {sqlstate} Message: {message}")
        conn.rollback() # Rollback on error
        return False, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred during checkout: {str(e)}")
        conn.rollback()
        return False, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def add_advanced_visitor(visitor_data):
    """Adds a new advanced check-in visitor record to the database."""
    conn = create_connection()
    if not conn:
        return False, "Database connection failed"

    cursor = conn.cursor()

    # Convert the advance check-in time from string to datetime
    try:
        advance_checkin_time = datetime.fromisoformat(visitor_data.get('AdvanceCheckInTime').replace('Z', '+00:00'))
    except (ValueError, AttributeError) as e:
        logging.error(f"Invalid advance check-in time format: {e}")
        return False, f"Invalid advance check-in time format: {e}"

    sql = f"""
        INSERT INTO {DB_TABLE} (
            GuestFirstName, GuestLastName, VisitorType, Branch, DepartmentVisited,
            VendorName, BadgeNumber, HostEmployeeName, Comments, 
            ColleagueFirstName, ColleagueLastName, AdvanceCheckInTime,
            SubmissionTime, IsAdvanceCheckIn, SubmitterIPAddress, Status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, 'Pending')
    """
    params = (
        visitor_data.get('GuestFirstName'),
        visitor_data.get('GuestLastName'),
        visitor_data.get('VisitorType'),
        visitor_data.get('Branch'),
        visitor_data.get('DepartmentVisited'),
        visitor_data.get('VendorName'),
        visitor_data.get('BadgeNumber'),
        visitor_data.get('HostEmployeeName'),
        visitor_data.get('Comments'),
        visitor_data.get('ColleagueFirstName'),
        visitor_data.get('ColleagueLastName'),
        advance_checkin_time,
        visitor_data.get('IsAdvanceCheckIn', True),
        visitor_data.get('SubmitterIPAddress')
    )

    try:
        logging.info(f"Executing SQL for advanced check-in: {sql} with params: {params}")
        cursor.execute(sql, params)
        conn.commit() # Commit the transaction
        logging.info("Advanced check-in visitor added successfully.")
        return True, "Advanced check-in visitor added successfully."
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to add advanced check-in visitor. SQLSTATE: {sqlstate} Message: {message}")
        conn.rollback() # Rollback on error
        return False, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        conn.rollback()
        return False, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_pending_visitors():
    """Retrieves all pending (pre-registered) visitor records, ordered by AdvanceCheckInTime."""
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    cursor = conn.cursor()
    visitors = []
    sql = f"""
        SELECT
            VisitorID, GuestFirstName, GuestLastName, VisitorType, Branch, DepartmentVisited,
            VendorName, BadgeNumber, HostEmployeeName, Comments,
            AdvanceCheckInTime, SubmissionTime, ColleagueFirstName, ColleagueLastName, Status
        FROM {DB_TABLE}
        WHERE Status = 'Pending'
        ORDER BY AdvanceCheckInTime ASC
    """
    try:
        cursor.execute(sql)
        # Get column names from cursor description
        columns = [column[0] for column in cursor.description]
        # Fetch rows and convert to list of dictionaries
        visitors = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logging.info(f"Retrieved {len(visitors)} pending visitor records.")
        return visitors, None
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to retrieve pending visitors. SQLSTATE: {sqlstate} Message: {message}")
        return None, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching pending visitors: {str(e)}")
        return None, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def checkin_pending_visitor(visitor_id, badge_number):
    """Updates a pending visitor's status to 'CheckedIn', sets the CheckInTime, and assigns a badge."""
    conn = create_connection()
    if not conn:
        return False, "Database connection failed"

    cursor = conn.cursor()
    sql = f"""
        UPDATE {DB_TABLE}
        SET Status = 'CheckedIn', CheckInTime = GETDATE(), BadgeNumber = ?
        WHERE VisitorID = ? AND Status = 'Pending'
    """
    params = (badge_number, visitor_id)

    try:
        logging.info(f"Checking in pending visitor ID: {visitor_id} with badge: {badge_number}")
        cursor.execute(sql, params)
        # Check if any row was actually updated
        if cursor.rowcount == 0:
            conn.rollback() # Rollback if no rows affected
            logging.warning(f"Pending visitor ID {visitor_id} not found or already checked in.")
            return False, "Visitor not found or already checked in."

        conn.commit() # Commit the transaction
        logging.info(f"Pending visitor ID {visitor_id} checked in successfully.")
        return True, "Visitor checked in successfully."
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        message = ex.args[1]
        logging.error(f"Failed to check in pending visitor ID {visitor_id}. SQLSTATE: {sqlstate} Message: {message}")
        conn.rollback() # Rollback on error
        return False, f"Database error: {message}"
    except Exception as e:
        logging.error(f"An unexpected error occurred during check-in: {str(e)}")
        conn.rollback()
        return False, f"An unexpected error occurred: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
