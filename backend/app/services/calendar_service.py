import os.path
import datetime as dt

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """
    Initializes and returns the Google Calendar API service client
    using Service Account credentials.
    """
    creds = None
    credentials_path = settings.GOOGLE_CALENDAR_CREDENTIALS_PATH

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Service account key file not found at '{credentials_path}'. "
                                "Please follow the instructions to create and place the file.")

    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
    except Exception as e:
        raise ValueError(f"Failed to load service account credentials: {e}")

    return build("calendar", "v3", credentials=creds)


def schedule_viewing(user_email: str, property_address: str, time_str: str) -> str:
    """
    Schedules a new event on Google Calendar.
    """
    try:
        service = get_calendar_service()
        
        start_time = dt.datetime.fromisoformat(time_str)
        end_time = start_time + dt.timedelta(hours=1)

        event = {
            "summary": f"Property Viewing: {property_address}",
            "location": property_address,
            "description": f"Viewing scheduled for {property_address} with {user_email}.",
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "America/New_York",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "America/New_York",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 30},
                ],
            },
        }

        calendar_id = 'primary' 

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return created_event.get("htmlLink")

    except HttpError as error:
        print(f"An error occurred: {error}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during scheduling: {e}")
        raise