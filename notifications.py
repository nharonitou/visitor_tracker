# still need webhook created, don't have access/permission
import requests
import os
import logging
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()


TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL', 'YOUR_PLACEHOLDER_WEBHOOK_URL_HERE')

def send_teams_notification(visitor_data):
    """Sends a notification card to a Teams channel via webhook."""

    if not TEAMS_WEBHOOK_URL or TEAMS_WEBHOOK_URL == 'YOUR_PLACEHOLDER_WEBHOOK_URL_HERE':
        logging.warning("TEAMS_WEBHOOK_URL not configured or is placeholder. Skipping notification.")
        print("--- Skipping Teams Notification (Webhook URL not set) ---") # Add console message for clarity during testing
        return False # Indicate skipped/failed

    # Create the Adaptive Card payload
    card_payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4", # Check Teams compatibility if issues arise
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Visitor Check-In Alert",
                            "weight": "bolder",
                            "size": "medium",
                            "color": "accent" # Example color
                        },
                        {
                           "type": "TextBlock",
                           "text": f"{visitor_data.get('GuestFirstName')} {visitor_data.get('GuestLastName')} has arrived.",
                           "wrap": True
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                { "title": "Host:", "value": f"{visitor_data.get('HostEmployeeName', 'N/A')}" },
                                { "title": "Type:", "value": visitor_data.get('VisitorType', 'N/A') },
                                { "title": "Branch:", "value": visitor_data.get('Branch', 'N/A') },
                                { "title": "Badge:", "value": visitor_data.get('BadgeNumber', 'N/A') },
                                { "title": "Time:", "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S') }
                            ]
                        }
                        # Add comments if they exist 
                    ] + ([
                        {
                            "type": "TextBlock",
                            "text": "Comments:",
                            "weight": "bolder",
                            "wrap": True,
                            "separator": True
                        },
                        {
                            "type": "TextBlock",
                            "text": visitor_data.get('Comments'),
                            "wrap": True
                        }
                    ] if visitor_data.get('Comments') else [])
                }
            }
        ]
    }

    headers = {'Content-Type': 'application/json'}

    try:
        logging.info(f"Sending Teams notification for {visitor_data.get('GuestLastName')}")
        response = requests.post(TEAMS_WEBHOOK_URL, headers=headers, json=card_payload, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logging.info(f"Teams notification sent successfully (Status code: {response.status_code}).")
        print(f"--- Teams notification sent successfully for {visitor_data.get('GuestLastName')} ---")
        return True
    except requests.exceptions.Timeout:
        logging.error("Failed to send Teams notification: Request timed out.")
        print("--- Failed to send Teams notification: Request timed out. ---")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Teams notification: {e}")
        print(f"--- Failed to send Teams notification: {e} ---") # Print error for debugging
        # also can inspect e.response.text for more details from Teams if available
        # logging.error(f"Response text: {e.response.text if e.response else 'N/A'}")
        return False
    except Exception as e:
         logging.error(f"An unexpected error occurred sending Teams notification: {e}")
         print(f"--- An unexpected error occurred sending Teams notification: {e} ---")
         return False